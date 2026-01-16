# Mail API 활용 가이드

## 개요

이메일 발송 기능은 SaaS 전환 시 활용할 수 있도록 API 형식만 미리 구축되어 있습니다.
현재 구축형 배포에서는 SMTP 설정 없이 배포되며, API 호출 시 "SMTP 설정이 완료되지 않았습니다" 응답을 반환합니다.

## 현재 상태 (구축형)

- 이메일 기능: 비활성화
- SMTP 환경변수: 미설정
- API 호출 결과: `{"success": false, "message": "SMTP 설정이 완료되지 않았습니다"}`

## SaaS 전환 시 활성화 방법

### 1. 중앙서버에 SMTP 환경변수 설정

```bash
# docker-compose.yml 또는 서버 환경변수
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=your-email@gmail.com
SMTP_FROM_NAME=Intown Platform
SMTP_USE_TLS=true
```

### 2. Gmail 앱 비밀번호 발급 방법

1. Google 계정 > 보안 > 2단계 인증 활성화
2. Google 계정 > 보안 > 앱 비밀번호 생성
3. 생성된 16자리 비밀번호를 `SMTP_PASS`에 설정

## API 엔드포인트

### SMTP 설정 조회
```
GET /mail/config
Authorization: Bearer {API_TOKEN}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "host": "smtp.gmail.com",
    "port": 587,
    "user": "your-email@gmail.com",
    "password": "****",
    "configured": true
  }
}
```

### 이메일 발송
```
POST /mail/send
Authorization: Bearer {API_TOKEN}
Content-Type: application/json
```

**요청:**
```json
{
  "to": "recipient@example.com",
  "subject": "이메일 제목",
  "body": "이메일 본문 (plain text)",
  "html": "<p>이메일 본문 (HTML, 선택)</p>",
  "from_name": "발신자 이름 (선택)"
}
```

**응답 (성공):**
```json
{
  "success": true,
  "data": {
    "message_id": "<abc123@mail.gmail.com>",
    "to": "recipient@example.com",
    "subject": "이메일 제목"
  },
  "message": "이메일 발송 성공"
}
```

### 대량 이메일 발송
```
POST /mail/send-bulk
Authorization: Bearer {API_TOKEN}
Content-Type: application/json
```

**요청:**
```json
{
  "to": ["user1@example.com", "user2@example.com"],
  "subject": "이메일 제목",
  "body": "이메일 본문"
}
```

### SMTP 연결 테스트
```
POST /mail/test
Authorization: Bearer {API_TOKEN}
```

## 클라이언트 호출 예시

### Python
```python
import httpx

MAIL_API_URL = "http://192.168.0.88:8000"
API_TOKEN = "your-api-token"

# 이메일 발송
response = httpx.post(
    f"{MAIL_API_URL}/mail/send",
    headers={"Authorization": f"Bearer {API_TOKEN}"},
    json={
        "to": "user@example.com",
        "subject": "테스트 이메일",
        "body": "안녕하세요, 테스트 이메일입니다."
    }
)
print(response.json())
```

### JavaScript
```javascript
const MAIL_API_URL = process.env.MAIL_API_URL || 'http://192.168.0.88:8000';

async function sendEmail(to, subject, body) {
    const response = await fetch(`${MAIL_API_URL}/mail/send`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${API_TOKEN}`
        },
        body: JSON.stringify({ to, subject, body })
    });
    return response.json();
}
```

## 환경변수 참조

Central Server 배포 시 다음 환경변수가 자동 설정됩니다:

```
MAIL_API_URL=http://{서버IP}:{API포트}
```

이 URL을 사용하여 Mail API를 호출할 수 있습니다.

## 보안 고려사항

1. **SMTP 비밀번호**: 절대 코드에 하드코딩하지 않음
2. **환경변수**: 서버에서만 설정, git에 포함하지 않음
3. **API 인증**: 모든 요청에 Bearer 토큰 필요
4. **TLS**: SMTP 연결 시 TLS 암호화 사용 권장
