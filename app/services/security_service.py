"""
고급 보안 서비스
"""
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import asyncio
import aioredis
from passlib.context import CryptContext
import jwt
from fastapi import Request
import re

from app.db.database import get_db
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)

class SecurityService:
    """고급 보안 서비스"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.failed_attempts = {}  # In-memory store for demo
        self.blocked_ips = set()
        
    async def analyze_login_security(self, db: Session, user_id: int, request: Request) -> Dict[str, any]:
        """로그인 보안 분석"""
        try:
            user_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            
            # 이상 로그인 패턴 감지
            suspicious_patterns = await self._detect_suspicious_patterns(
                db, user_id, user_ip, user_agent
            )
            
            # 지역 기반 분석
            location_analysis = await self._analyze_login_location(user_ip)
            
            # 디바이스 fingerprinting
            device_analysis = await self._analyze_device_fingerprint(request)
            
            # 위험 점수 계산
            risk_score = self._calculate_risk_score(
                suspicious_patterns, location_analysis, device_analysis
            )
            
            security_analysis = {
                "risk_score": risk_score,
                "risk_level": self._get_risk_level(risk_score),
                "suspicious_patterns": suspicious_patterns,
                "location_analysis": location_analysis,
                "device_analysis": device_analysis,
                "recommendations": self._generate_security_recommendations(risk_score),
                "timestamp": datetime.now().isoformat()
            }
            
            # 보안 로그 기록
            await self._log_security_event(db, user_id, "login_analysis", security_analysis)
            
            return security_analysis
            
        except Exception as e:
            logger.error(f"로그인 보안 분석 실패: {str(e)}")
            return {"risk_score": 0.5, "risk_level": "medium", "error": str(e)}
    
    async def implement_rate_limiting(self, request: Request, endpoint: str) -> Dict[str, any]:
        """요청 속도 제한"""
        try:
            client_ip = self._get_client_ip(request)
            
            # 엔드포인트별 제한 설정
            limits = {
                "login": {"requests": 5, "window": 300},  # 5분에 5회
                "register": {"requests": 3, "window": 3600},  # 1시간에 3회
                "diagnosis": {"requests": 10, "window": 3600},  # 1시간에 10회
                "default": {"requests": 100, "window": 3600}  # 1시간에 100회
            }
            
            limit_config = limits.get(endpoint, limits["default"])
            
            # 요청 횟수 체크
            is_limited, remaining, reset_time = await self._check_rate_limit(
                client_ip, endpoint, limit_config
            )
            
            if is_limited:
                # IP 차단 고려
                await self._consider_ip_blocking(client_ip, endpoint)
                
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "message": "요청 한도를 초과했습니다."
                }
            
            return {
                "allowed": True,
                "remaining": remaining,
                "reset_time": reset_time
            }
            
        except Exception as e:
            logger.error(f"속도 제한 체크 실패: {str(e)}")
            return {"allowed": True, "remaining": 0}
    
    async def validate_password_strength(self, password: str) -> Dict[str, any]:
        """비밀번호 강도 검증"""
        try:
            score = 0
            feedback = []
            
            # 길이 체크
            if len(password) >= 8:
                score += 20
            else:
                feedback.append("최소 8자 이상이어야 합니다")
            
            if len(password) >= 12:
                score += 10
            
            # 문자 종류 체크
            if re.search(r'[a-z]', password):
                score += 15
            else:
                feedback.append("소문자가 포함되어야 합니다")
            
            if re.search(r'[A-Z]', password):
                score += 15
            else:
                feedback.append("대문자가 포함되어야 합니다")
            
            if re.search(r'\d', password):
                score += 15
            else:
                feedback.append("숫자가 포함되어야 합니다")
            
            if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                score += 15
            else:
                feedback.append("특수문자가 포함되어야 합니다")
            
            # 패턴 체크
            if not re.search(r'(.)\1{2,}', password):  # 같은 문자 3번 연속 x
                score += 10
            else:
                feedback.append("같은 문자를 3번 이상 연속 사용하지 마세요")
            
            # 일반적인 패턴 체크
            common_patterns = ['123', 'abc', 'qwe', 'password', '000']
            if not any(pattern in password.lower() for pattern in common_patterns):
                score += 10
            else:
                feedback.append("일반적인 패턴을 피해주세요")
            
            # 강도 등급 계산
            if score >= 80:
                strength = "very_strong"
            elif score >= 60:
                strength = "strong"
            elif score >= 40:
                strength = "medium"
            elif score >= 20:
                strength = "weak"
            else:
                strength = "very_weak"
            
            return {
                "score": score,
                "strength": strength,
                "feedback": feedback,
                "is_acceptable": score >= 40
            }
            
        except Exception as e:
            logger.error(f"비밀번호 강도 검증 실패: {str(e)}")
            return {"score": 0, "strength": "error", "is_acceptable": False}
    
    async def implement_2fa(self, db: Session, user_id: int, method: str = "totp") -> Dict[str, any]:
        """2단계 인증 구현"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "사용자를 찾을 수 없습니다"}
            
            if method == "totp":
                # TOTP 비밀키 생성
                secret = secrets.token_urlsafe(32)
                
                # QR 코드용 URL 생성
                qr_url = f"otpauth://totp/CampusON:{user.email}?secret={secret}&issuer=CampusON"
                
                # 사용자 데이터에 저장 (실제로는 암호화해서 저장)
                # user.totp_secret = self._encrypt_secret(secret)
                # db.commit()
                
                return {
                    "success": True,
                    "method": "totp",
                    "secret": secret,
                    "qr_url": qr_url,
                    "backup_codes": self._generate_backup_codes()
                }
            
            elif method == "sms":
                # SMS 2FA 구현
                verification_code = self._generate_verification_code()
                
                # SMS 발송 (실제로는 SMS 서비스 연동)
                # await self._send_sms(user.phone, verification_code)
                
                return {
                    "success": True,
                    "method": "sms",
                    "message": "인증 코드가 발송되었습니다",
                    "expires_in": 300  # 5분
                }
            
            else:
                return {"success": False, "error": "지원하지 않는 2FA 방법입니다"}
                
        except Exception as e:
            logger.error(f"2FA 구현 실패: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def audit_security_events(self, db: Session, days: int = 30) -> Dict[str, any]:
        """보안 이벤트 감사"""
        try:
            # 실제로는 보안 로그 테이블에서 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 가상의 보안 이벤트 데이터
            security_events = {
                "failed_logins": 45,
                "successful_logins": 1234,
                "blocked_ips": len(self.blocked_ips),
                "suspicious_activities": 12,
                "2fa_activations": 23,
                "password_changes": 67
            }
            
            # 위험 분석
            risk_analysis = {
                "high_risk_events": 3,
                "medium_risk_events": 9,
                "low_risk_events": 45,
                "trends": {
                    "failed_login_trend": "+15%",
                    "suspicious_activity_trend": "-8%",
                    "security_score": 8.2
                }
            }
            
            # 권장사항
            recommendations = [
                "비밀번호 정책 강화 검토",
                "2FA 활성화 사용자 확대",
                "의심스러운 IP 모니터링 강화",
                "보안 교육 실시"
            ]
            
            return {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "security_events": security_events,
                "risk_analysis": risk_analysis,
                "recommendations": recommendations,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"보안 감사 실패: {str(e)}")
            return {"error": str(e)}
    
    async def implement_session_security(self, db: Session, user_id: int, session_token: str) -> Dict[str, any]:
        """세션 보안 관리"""
        try:
            # 세션 유효성 검증
            session_data = await self._validate_session(session_token)
            
            if not session_data:
                return {"valid": False, "reason": "invalid_session"}
            
            # 동시 세션 제한
            active_sessions = await self._get_active_sessions(user_id)
            
            if len(active_sessions) > 3:  # 최대 3개 세션
                # 가장 오래된 세션 무효화
                await self._invalidate_oldest_session(user_id)
            
            # 세션 하이재킹 감지
            hijack_detected = await self._detect_session_hijacking(
                user_id, session_token, session_data
            )
            
            if hijack_detected:
                await self._invalidate_all_sessions(user_id)
                return {
                    "valid": False,
                    "reason": "session_hijacking_detected",
                    "action": "all_sessions_invalidated"
                }
            
            # 세션 갱신
            new_token = await self._refresh_session(session_token)
            
            return {
                "valid": True,
                "new_token": new_token,
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"세션 보안 관리 실패: {str(e)}")
            return {"valid": False, "reason": "security_error"}
    
    # Private helper methods
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def _detect_suspicious_patterns(self, db: Session, user_id: int, ip: str, user_agent: str) -> List[str]:
        """의심스러운 패턴 감지"""
        patterns = []
        
        # 여러 IP에서 동시 로그인
        # 비정상적인 시간대 로그인
        # 다른 지역에서의 연속 로그인
        # User-Agent 급변
        
        # 실제 구현에서는 데이터베이스 쿼리로 패턴 분석
        
        return patterns
    
    async def _analyze_login_location(self, ip: str) -> Dict[str, any]:
        """로그인 위치 분석"""
        # 실제로는 IP 지역 서비스 연동
        return {
            "country": "KR",
            "city": "Seoul",
            "is_usual_location": True,
            "is_vpn": False,
            "is_tor": False
        }
    
    def _generate_backup_codes(self) -> List[str]:
        """백업 코드 생성"""
        return [f"{secrets.randbelow(10000):04d}-{secrets.randbelow(10000):04d}" for _ in range(10)]
    
    def _generate_verification_code(self) -> str:
        """인증 코드 생성"""
        return f"{secrets.randbelow(1000000):06d}"

# 싱글톤 인스턴스
security_service = SecurityService() 