#!/usr/bin/env python3
import asyncio
import httpx

async def quick_test():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://localhost:8000/api/diagnosis/result/24/detailed')
        if response.status_code == 200:
            data = response.json()
            basic = data.get('basic_result', {})
            print(f'✅ API 작동: 학습수준={basic.get("learning_level", 0)}, 정답률={basic.get("accuracy_rate", 0)*100:.1f}%')
            print(f'📊 총 문항: {basic.get("total_questions", 0)}, 맞힌 문항: {basic.get("correct_answers", 0)}')
        else:
            print(f'❌ API 오류: {response.status_code} - {response.text}')

asyncio.run(quick_test()) 