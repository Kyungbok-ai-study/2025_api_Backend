import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from io import StringIO
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# LlamaParse 설정
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_API_KEY", "llx-ZDuPItwP3P2boavegqhNubFo3xFZIxSSxJoqzYN1NU8H3BNl")

# 특수문자 변환 맵
NUMBER_MAP = {
    '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
    '㉠': '1', '㉡': '2', '㉢': '3', '㉣': '4', '㉤': '5',
    'ⓐ': '1', 'ⓑ': '2', 'ⓒ': '3', 'ⓓ': '4', 'ⓔ': '5',
    '⑴': '1', '⑵': '2', '⑶': '3', '⑷': '4', '⑸': '5',
    '㈀': '1', '㈁': '2', '㈂': '3', '㈃': '4', '㈄': '5',
    '㊀': '1', '㊁': '2', '㊂': '3', '㊃': '4', '㊄': '5'
}

class LlamaParser:
    def __init__(self):
        self.laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5,
            detect_vertical=True,
            all_texts=True
        )

    def normalize_number(self, text: str) -> str:
        """특수문자를 숫자로 변환"""
        for k, v in NUMBER_MAP.items():
            text = text.replace(k, v)
        return text

    def extract_year_and_round(self, filename: str) -> Tuple[str, str]:
        """파일명에서 년도와 회차 추출"""
        match = re.search(r'(\d{4})년도.*?제(\d+)회', filename)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def extract_period_number(self, filename: str) -> Optional[int]:
        """파일명에서 교시 정보 추출"""
        match = re.search(r'(\d+)교시', filename)
        if match:
            return int(match.group(1))
        return None

    def parse_question_content(self, text: str) -> Tuple[str, List[str], bool]:
        """문제 내용, 보기, 박스형 여부 추출"""
        lines = text.split('\n')
        question_text = []
        choices = []
        is_box_type = False
        in_choices = False
        
        choice_pattern = re.compile(r'^[①②③④⑤]\s*\.*\s*(.+)')
        box_pattern = re.compile(r'[□■]+\s*(.+)')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 박스형 확인
            if re.search(r'[□■]', line):
                is_box_type = True
                
            choice_match = choice_pattern.match(line)
            box_match = box_pattern.match(line)
            
            if choice_match:
                in_choices = True
                choice_text = choice_match.group(1).strip()
                choices.append(choice_text)
            elif box_match:
                box_text = box_match.group(1).strip()
                if not in_choices:
                    question_text.append(f"[박스] {box_text}")
            elif not in_choices:
                question_text.append(line)
        
        return ' '.join(question_text), choices, is_box_type

    def extract_answers(self, answer_text: str, period: int) -> Dict[int, str]:
        """답안지에서 답안 추출"""
        answers = {}
        current_period = None
        
        period_pattern = re.compile(r'(\d+)교시')
        answer_pattern = re.compile(r'(?:문제\s*(\d+)[\.:\s]*)?(?:정답|최종답안)[:\s]*([1-5])')
        
        lines = answer_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            period_match = period_pattern.search(line)
            if period_match:
                current_period = int(period_match.group(1))
                continue
            
            if current_period == period:
                answer_matches = answer_pattern.finditer(line)
                for match in answer_matches:
                    question_num = int(match.group(1)) if match.group(1) else len(answers) + 1
                    answer = match.group(2)
                    answers[question_num] = answer
        
        return answers

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        try:
            output = StringIO()
            with open(pdf_path, 'rb') as pdf_file:
                extract_text_to_fp(pdf_file, output, laparams=self.laparams)
            return output.getvalue()
        except Exception as e:
            print(f"PDF 텍스트 추출 오류 ({pdf_path}): {str(e)}")
            return None

    def parse_pdf(self, pdf_path: Path, answer_path: Optional[Path] = None) -> Dict:
        """PDF 파일 파싱"""
        try:
            # PDF 문서 로드
            text = self.extract_text_from_pdf(str(pdf_path))
            if not text:
                raise Exception("PDF 파싱 실패")

            # 메타데이터 추출
            year, round_num = self.extract_year_and_round(pdf_path.name)
            period = self.extract_period_number(pdf_path.name)
            subject = "물리치료사" if "물리치료사" in pdf_path.name else "작업치료사"

            # 답안 파일 파싱
            answers = {}
            if answer_path and answer_path.exists():
                answer_text = self.extract_text_from_pdf(str(answer_path))
                if answer_text:
                    answers = self.extract_answers(answer_text, period)

            # 문제 추출 및 구조화
            questions = []
            question_pattern = re.compile(r'(\d+)\s*[\.。]\s*(.+?)(?=(?:\d+\s*[\.。])|$)', re.DOTALL)
            
            # 문서 텍스트 정규화
            text = self.normalize_number(text)
            matches = list(question_pattern.finditer(text))

            # 문제 번호 자동 정렬
            for idx, match in enumerate(matches, 1):
                original_number = int(match.group(1))
                question_text = match.group(2).strip()
                
                text, choices, is_box_type = self.parse_question_content(question_text)
                
                questions.append({
                    "original_number": original_number,
                    "number": idx,
                    "text": text,
                    "choices": choices,
                    "is_box_type": is_box_type,
                    "answer": answers.get(original_number) or answers.get(idx)
                })

            # 정렬된 문제 번호로 재정렬
            questions.sort(key=lambda x: x["number"])

            return {
                "year": year,
                "round": round_num,
                "period": period,
                "subject": subject,
                "total_questions": len(questions),
                "questions": questions,
                "metadata": {
                    "source_file": pdf_path.name,
                    "answer_file": answer_path.name if answer_path else None,
                    "subject": subject,
                    "year": year,
                    "round": round_num,
                    "period": period
                }
            }

        except Exception as e:
            print(f"PDF 파싱 오류 ({pdf_path}): {str(e)}")
            return None 