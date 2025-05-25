import os
import json
import asyncio
from pathlib import Path
import re
import fitz  # PyMuPDF
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from llama_parser import LlamaParser

DATA_DIR = Path("C:/Users/jaewo/Desktop/study/api_server/data")
JSON_OUTPUT_DIR = DATA_DIR / "json"
ANSWER_DIR = DATA_DIR / "answer"
TEST_DIR = DATA_DIR / "test"

LLAMA_API_KEY = "llx-ZDuPItwP3P2boavegqhNubFo3xFZIxSSxJoqzYN1NU8H3BNl"

# 특수문자 변환 맵
NUMBER_MAP = {
    '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
    '㉠': '1', '㉡': '2', '㉢': '3', '㉣': '4', '㉤': '5',
    'ⓐ': '1', 'ⓑ': '2', 'ⓒ': '3', 'ⓓ': '4', 'ⓔ': '5',
    '⑴': '1', '⑵': '2', '⑶': '3', '⑷': '4', '⑸': '5',
    '㈀': '1', '㈁': '2', '㈂': '3', '㈃': '4', '㈄': '5',
    '㊀': '1', '㊁': '2', '㊂': '3', '㊃': '4', '㊄': '5'
}

def normalize_number(text: str) -> str:
    """특수문자를 숫자로 변환"""
    for k, v in NUMBER_MAP.items():
        text = text.replace(k, v)
    return text

def extract_year_and_round(filename: str) -> Tuple[str, str]:
    """파일명에서 년도와 회차 추출"""
    match = re.search(r'(\d{4})년도.*?제(\d+)회', filename)
    if match:
        return match.group(1), match.group(2)
    return None, None

def extract_period_number(filename: str) -> Optional[int]:
    """파일명에서 교시 정보 추출"""
    match = re.search(r'(\d+)교시', filename)
    if match:
        return int(match.group(1))
    return None

async def find_matching_answer_file(test_file: Path) -> Path:
    """문제 파일에 매칭되는 답안 파일 찾기"""
    parser = LlamaParser()
    test_year, test_round = parser.extract_year_and_round(test_file.name)
    test_period = parser.extract_period_number(test_file.name)
    
    if not all([test_year, test_round, test_period]):
        return None
    
    subject_type = "physical_therapy" if "물리치료사" in test_file.name else "occupational_therapy"
    answer_dir = ANSWER_DIR / subject_type
    
    for answer_file in answer_dir.glob("*.pdf"):
        answer_year, answer_round = parser.extract_year_and_round(answer_file.name)
        if (answer_year == test_year and answer_round == test_round):
            return answer_file
    
    return None

def extract_text_with_mupdf_sync(pdf_path: str) -> dict:
    """PyMuPDF를 사용하여 PDF에서 텍스트 추출"""
    doc = None
    try:
        # PDF 파일 열기
        doc = fitz.open(pdf_path)
        if not doc:
            raise Exception(f"Could not open PDF file: {pdf_path}")
            
        text_content = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 텍스트 블록 추출
            blocks = page.get_text("blocks")
            # y0 좌표로 정렬하여 올바른 읽기 순서 보장
            blocks.sort(key=lambda b: (b[1], b[0]))  # y0, x0 기준 정렬
            
            page_text = []
            for block in blocks:
                text = block[4].strip()
                if text and not any(header in text for header in ['물리치료사', '작업치료사', '면허시험']):
                    # 문제 번호나 보기 번호 앞에 개행 추가
                    text = re.sub(r'(\d+)\s*\.\s*', r'\n\1. ', text)
                    text = re.sub(r'([①②③④⑤])\s*', r'\n\1 ', text)
                    page_text.append(text)
            
            text_content.append('\n'.join(page_text))
        
        full_text = '\n'.join(text_content)
        
        # 중복된 개행 제거 및 정리
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        
        result = {
            "raw_text": normalize_number(full_text),
            "metadata": {
                "page_count": len(doc),
                "file_name": os.path.basename(pdf_path)
            }
        }
        
        return result
        
    except Exception as e:
        print(f"PDF 파싱 실패 ({pdf_path}): {str(e)}")
        return None
        
    finally:
        # 문서가 열려있다면 반드시 닫기
        if doc:
            doc.close()

async def extract_text_with_mupdf(pdf_path: Path) -> dict:
    """비동기적으로 PDF 텍스트 추출"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, extract_text_with_mupdf_sync, str(pdf_path))

def extract_question_content(text: str) -> Tuple[str, List[str], bool]:
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

def extract_answers_from_text(text: str, period: int) -> Dict[int, str]:
    """답안지에서 최종답안 추출"""
    answers = {}
    current_period = None
    
    # 정규표현식 패턴
    period_pattern = re.compile(r'(\d+)교시')
    answer_pattern = re.compile(r'(?:문제\s*(\d+)[\.:\s]*)?(?:정답|최종답안)[:\s]*([1-5])')
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 교시 확인
        period_match = period_pattern.search(line)
        if period_match:
            current_period = int(period_match.group(1))
            continue
        
        # 현재 교시가 찾는 교시와 일치할 때만 답안 처리
        if current_period == period:
            answer_matches = answer_pattern.finditer(line)
            for match in answer_matches:
                question_num = int(match.group(1)) if match.group(1) else len(answers) + 1
                answer = match.group(2)
                answers[question_num] = answer
    
    return answers

async def process_pdf_file(pdf_path: Path) -> dict:
    """PDF 파일 처리 및 구조화"""
    try:
        parser = LlamaParser()
        answer_file = await find_matching_answer_file(pdf_path)
        
        if not answer_file:
            print(f"매칭되는 답안 파일을 찾을 수 없음: {pdf_path}")
            return None
            
        result = parser.parse_pdf(pdf_path, answer_file)
        if not result:
            print(f"PDF 파싱 실패: {pdf_path}")
            return None
            
        return result
        
    except Exception as e:
        print(f"파일 처리 오류 {pdf_path}: {str(e)}")
        return None

async def save_json_file(data: dict, output_path: Path):
    """JSON 파일 저장"""
    async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

async def process_directory(input_dir: Path, output_dir: Path):
    """디렉토리 내 PDF 파일 처리"""
    if not input_dir.exists():
        print(f"입력 디렉토리를 찾을 수 없음: {input_dir}")
        return
        
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"PDF 파일을 찾을 수 없음: {input_dir}")
        return
        
    tasks = []
    
    with tqdm(total=len(pdf_files), desc="PDF 파일 처리 중") as pbar:
        for pdf_file in pdf_files:
            try:
                print(f"\n처리 중: {pdf_file}")
                data = await process_pdf_file(pdf_file)
                
                if data:  # 성공적으로 처리된 경우에만 저장
                    output_file = output_dir / f"{pdf_file.stem}.json"
                    tasks.append(save_json_file(data, output_file))
                
            except Exception as e:
                print(f"파일 처리 오류 {pdf_file}: {str(e)}")
            finally:
                pbar.update(1)
    
    if tasks:
        await asyncio.gather(*tasks)

async def main():
    """메인 함수"""
    try:
        JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        tasks = []
        for subject_dir in ["physical_therapy", "occupational_therapy"]:
            input_dir = TEST_DIR / subject_dir
            if not input_dir.exists():
                print(f"디렉토리를 찾을 수 없음: {input_dir}")
                continue
                
            output_dir = JSON_OUTPUT_DIR / subject_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            
            tasks.append(process_directory(input_dir, output_dir))
        
        if tasks:
            await asyncio.gather(*tasks)
        else:
            print("처리할 디렉토리가 없습니다.")
            
    except Exception as e:
        print(f"프로그램 실행 중 오류 발생: {str(e)}")
        
if __name__ == "__main__":
    asyncio.run(main()) 