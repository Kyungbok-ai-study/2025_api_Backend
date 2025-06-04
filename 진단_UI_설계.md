# �� 진단 테스트 UI 설계 가이드 (1문제 30선택지 형태)

## 📱 화면 구성

### 1. 진단 테스트 시작 화면
```
┌─────────────────────────────────────┐
│ 🎯 컴퓨터과학 진단 테스트           │
├─────────────────────────────────────┤
│ • 총 1문항                          │
│ • 30개 선택지 중 정답 찾기          │
│ • 제한시간: 60분                    │
│ • 난이도: 혼재된 선택지              │
│                                     │
│ [📝 진단 테스트 시작하기]           │
└─────────────────────────────────────┘
```

### 2. 메인 테스트 화면 (1문제 30선택지) - 핵심!
```
┌──────────────────────────────────────────────────────────────┐
│ 🎯 컴퓨터과학 진단 테스트  ⏰ 52:30  👤 홍길동              │
│ 📝 문제 풀이 중... | 🎯 30개 중 정답 찾기 | 📊 자동 저장   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 🎯 선택지 (30개 중 정답 1개를 찾으세요)                     │
│                                                              │
│  1⃣ cemputer    6⃣ compiter   11⃣ computar   16⃣ competer   │
│  2⃣ mebuter     7⃣ combuter   12⃣ computer    17⃣ computerr  │
│  3⃣ compter     8⃣ compoter   13⃣ computor    18⃣ conputer   │
│  4⃣ conmputer   9⃣ computee   14⃣ computter   19⃣ compuuter  │
│  5⃣ computar    🔟 compuer    15⃣ computeer   20⃣ computre   │
│                                                              │
│  21⃣ computar   26⃣ coumputer                                │
│  22⃣ compuuter  27⃣ computar                                 │
│  23⃣ computer   28⃣ compuder                                 │
│  24⃣ computor   29⃣ computar                                 │
│  25⃣ computre   30⃣ compiter                                 │
└──────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│ 📝 문제                                                      │
│                                                              │
│ 다음 중 "컴퓨터"의 올바른 영어 스펠링은 무엇입니까?                 │
│                                                              │
│ 💡 힌트: 정확한 스펠링을 찾아보세요                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ ✅ 선택된 답안: 23번 - computer                               │
│ ⏱️ 답변 시간: 02:45                                          │
│ 📊 확신도: 매우 확신함                                         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ [🔄 답변 변경] [💡 힌트 보기] [✅ 최종 제출] [💾 임시 저장]     │
└──────────────────────────────────────────────────────────────┘
```

### 2-1. 선택지 영역 세부 디자인 (6x5 그리드)
```
🎯 30개 선택지 그리드
┌─────────────────────────────────────────────────────────────┐
│  1⃣ cemputer    6⃣ compiter   11⃣ computar   16⃣ competer   │
│  2⃣ mebuter     7⃣ combuter   12⃣ computer    17⃣ computerr  │
│  3⃣ compter     8⃣ compoter   13⃣ computor    18⃣ conputer   │
│  4⃣ conmputer   9⃣ computee   14⃣ computter   19⃣ compuuter  │
│  5⃣ computar    🔟 compuer    15⃣ computeer   20⃣ computre   │
│                                                             │
│  21⃣ computar   26⃣ coumputer                               │
│  22⃣ compuuter  27⃣ computar                                │
│  23⃣ computer   28⃣ compuder     ← 선택된 상태 (파란 배경) │
│  24⃣ computor   29⃣ computar                                │
│  25⃣ computre   30⃣ compiter                                │
└─────────────────────────────────────────────────────────────┘

상태 표시:
⚪ = 미선택 (기본 상태)
🔵 = 선택됨 (파란 배경, 체크마크)
🤔 = 고민 중 (노란 배경, 임시 표시)
❌ = 제외됨 (회색, 사용자가 명시적으로 제외)

호버 효과:
- 마우스 올리면 해당 선택지 확대 표시
- 클릭하면 선택/해제 토글
- 더블클릭하면 확신하고 바로 제출
```

### 2-2. 모바일 반응형 (세로 스크롤)
```
┌───────────────────────┐
│ 🎯 진단테스트          │
│ ⏰ 52:30             │
└───────────────────────┘

┌───────────────────────┐
│ 📝 문제               │
│                       │
│ "컴퓨터"의 올바른     │
│ 영어 스펠링은?        │
│                       │
│ 💡 정확한 스펠링 찾기 │
└───────────────────────┘

┌───────────────────────┐ ← 스크롤 가능한 선택지
│ 🎯 30개 선택지        │
│                       │
│  1⃣ cemputer         │
│  2⃣ mebuter          │
│  3⃣ compter          │
│  4⃣ conmputer        │
│  5⃣ computar         │
│  6⃣ compiter         │
│  7⃣ combuter         │
│  8⃣ compoter         │
│  9⃣ computee         │
│  🔟 compuer          │
│  11⃣ computar        │
│  12⃣ computer  [✓]   │ ← 선택된 상태
│  13⃣ computor        │
│  ...                 │
│  30⃣ compiter        │
└───────────────────────┘

┌───────────────────────┐
│ ✅ 선택: 12번 computer │
│ [🔄] [💡] [✅] [💾]  │
└───────────────────────┘
```

### 3. 최종 제출 전 확인 화면
```
┌─────────────────────────────────────┐
│ 📝 답안 제출 전 최종 확인           │
├─────────────────────────────────────┤
│                                     │
│ 🎯 선택한 답안: 23번                │
│ 📝 답안 내용: computer              │
│ ⏱️ 소요 시간: 2분 45초              │
│ 📊 확신도: 매우 확신함              │
│                                     │
│ ⚠️  한 번 제출하면 수정할 수 없습니다 │
│    정말 제출하시겠습니까?           │
│                                     │
│ [🔄 답변 수정] [✅ 최종 제출]       │
└─────────────────────────────────────┘
```

### 4. 결과 화면
```
┌─────────────────────────────────────┐
│ 🎉 진단 테스트 완료!                │
├─────────────────────────────────────┤
│ 📝 문제: 컴퓨터 스펠링 찾기         │
│ ✅ 선택 답안: 23번 - computer       │
│ 🎯 정답: 23번 - computer            │
│ 📊 결과: 정답! 🎉                  │
│                                     │
│ ⏱️ 소요 시간: 2분 45초              │
│ 🧠 학습 수준 분석:                  │
│                                     │
│ 📈 언어 능력: 우수 ✅              │
│ • 정확한 스펠링 인식 능력           │
│ • 유사한 단어 구별 능력             │
│ • 집중력 및 주의력                  │
│                                     │
│ 💪 강점: 기초 어휘력               │
│ 📝 개선점: -                       │
│                                     │
│ [📊 상세 분석] [🔄 다시하기]        │
└─────────────────────────────────────┘
```

## 🔧 프론트엔드 구현 포인트

### React/Vue 컴포넌트 구조 (1문제 30선택지)
```javascript
// 1. 메인 진단 테스트 컴포넌트
DiagnosisTest.vue/jsx
├── QuestionDisplay.vue/jsx         // 문제 표시
├── ChoicesGrid.vue/jsx             // 30개 선택지 그리드
├── AnswerStatus.vue/jsx            // 선택된 답안 상태
├── NavigationPanel.vue/jsx         // 제출/저장 컨트롤
└── SubmissionCheck.vue/jsx         // 제출 전 확인

// 2. 선택지 상태 관리
const choicesState = {
  selectedChoice: null,              // 선택된 선택지 번호 (1-30)
  selectedContent: '',               // 선택된 선택지 내용
  confidenceLevel: 'medium',         // 확신도 (low/medium/high)
  eliminatedChoices: new Set(),      // 제외된 선택지들
  startTime: Date.now(),             // 시작 시간
  tempSaveTime: null                 // 마지막 임시 저장 시간
}
```

### 30개 선택지 그리드 구현
```javascript
// ChoicesGrid.vue
<template>
  <div class="choices-grid-container">
    <h3 class="choices-title">🎯 선택지 (30개 중 정답 1개를 찾으세요)</h3>
    
    <div class="choices-grid">
      <div 
        v-for="(choice, index) in choices" 
        :key="index + 1"
        :class="getChoiceClass(index + 1)"
        @click="selectChoice(index + 1)"
        @dblclick="submitWithChoice(index + 1)"
        @contextmenu.prevent="toggleElimination(index + 1)"
      >
        <span class="choice-number">{{ index + 1 }}⃣</span>
        <span class="choice-content">{{ choice.content }}</span>
        
        <!-- 선택 상태 표시 -->
        <div v-if="selectedChoice === index + 1" class="choice-selected">
          ✓
        </div>
        
        <!-- 제외 상태 표시 -->
        <div v-if="eliminatedChoices.has(index + 1)" class="choice-eliminated">
          ❌
        </div>
      </div>
    </div>
    
    <!-- 선택지 필터링 옵션 -->
    <div class="choices-filter">
      <button @click="showAll">전체 보기</button>
      <button @click="showSelected">선택된 것만</button>
      <button @click="showEliminated">제외된 것만</button>
      <button @click="clearEliminated">제외 해제</button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    choices: Array,
    selectedChoice: Number,
    eliminatedChoices: Set
  },
  
  methods: {
    getChoiceClass(choiceNum) {
      const baseClass = 'choice-item';
      
      if (choiceNum === this.selectedChoice) {
        return `${baseClass} selected`;
      } else if (this.eliminatedChoices.has(choiceNum)) {
        return `${baseClass} eliminated`;
      } else {
        return baseClass;
      }
    },
    
    selectChoice(choiceNum) {
      if (this.eliminatedChoices.has(choiceNum)) {
        return; // 제외된 선택지는 선택 불가
      }
      
      this.$emit('choice-selected', {
        number: choiceNum,
        content: this.choices[choiceNum - 1].content
      });
    },
    
    submitWithChoice(choiceNum) {
      this.selectChoice(choiceNum);
      this.$emit('quick-submit');
    },
    
    toggleElimination(choiceNum) {
      this.$emit('toggle-elimination', choiceNum);
    }
  }
}
</script>
```

### CSS 스타일링 (30선택지 그리드)
```css
/* 메인 레이아웃 */
.diagnosis-test {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100vh;
}

/* 문제 영역 */
.question-section {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  border-left: 4px solid #3b82f6;
}

.question-content {
  font-size: 20px;
  line-height: 1.6;
  color: #1f2937;
  margin-bottom: 16px;
  text-align: center;
}

.question-hint {
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
  padding: 12px 16px;
  border-radius: 0 8px 8px 0;
  font-size: 14px;
  color: #92400e;
  margin-top: 16px;
}

/* 30개 선택지 그리드 */
.choices-grid-container {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08);
}

.choices-title {
  text-align: center;
  color: #1f2937;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
}

.choices-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  grid-template-rows: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.choice-item {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  min-height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  font-size: 13px;
  text-align: center;
}

.choice-number {
  font-weight: 600;
  color: #6b7280;
  font-size: 11px;
  margin-bottom: 4px;
}

.choice-content {
  color: #374151;
  font-weight: 500;
  line-height: 1.2;
}

/* 선택지 상태 스타일 */
.choice-item:hover:not(.eliminated) {
  border-color: #3b82f6;
  background: #f8fafc;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.choice-item.selected {
  border-color: #10b981;
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #047857;
  transform: scale(1.05);
  box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
}

.choice-item.selected .choice-number {
  color: #047857;
}

.choice-item.eliminated {
  background: #f3f4f6;
  border-color: #d1d5db;
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.choice-selected {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: bold;
  animation: checkIn 0.3s ease-out;
}

.choice-eliminated {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  background: #ef4444;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: bold;
}

@keyframes checkIn {
  0% {
    opacity: 0;
    transform: scale(0) rotate(180deg);
  }
  100% {
    opacity: 1;
    transform: scale(1) rotate(0deg);
  }
}

/* 선택지 필터 */
.choices-filter {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.choices-filter button {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.choices-filter button:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

/* 답안 상태 영역 */
.answer-status {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}

.selected-answer {
  color: #047857;
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 8px;
}

.answer-time {
  color: #6b7280;
  font-size: 14px;
  margin-bottom: 8px;
}

.confidence-level {
  display: flex;
  gap: 8px;
  justify-content: center;
  align-items: center;
}

.confidence-btn {
  padding: 4px 12px;
  border: 1px solid #d1d5db;
  border-radius: 20px;
  background: white;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.confidence-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

/* 모바일 반응형 */
@media (max-width: 768px) {
  .choices-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  
  .choice-item {
    min-height: 50px;
    padding: 10px;
    flex-direction: row;
    justify-content: flex-start;
    text-align: left;
  }
  
  .choice-number {
    margin-right: 8px;
    margin-bottom: 0;
  }
  
  .choice-content {
    flex: 1;
  }
}

/* 태블릿 반응형 */
@media (max-width: 1024px) and (min-width: 769px) {
  .choices-grid {
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(10, 1fr);
  }
}
```

### JavaScript 상태 관리 (30선택지)
```javascript
// 30선택지 진단 테스트 상태 관리
class MultiChoiceState {
  constructor() {
    this.selectedChoice = null;
    this.selectedContent = '';
    this.eliminatedChoices = new Set();
    this.confidenceLevel = 'medium';
    this.startTime = Date.now();
    this.tempSaveTime = null;
    this.isSubmitted = false;
  }

  // 선택지 선택
  selectChoice(choiceNumber, choiceContent) {
    this.selectedChoice = choiceNumber;
    this.selectedContent = choiceContent;
    this.saveToLocalStorage();
  }

  // 선택지 제거/복원
  toggleElimination(choiceNumber) {
    if (this.eliminatedChoices.has(choiceNumber)) {
      this.eliminatedChoices.delete(choiceNumber);
    } else {
      this.eliminatedChoices.add(choiceNumber);
      
      // 제거된 선택지가 현재 선택된 것이면 선택 해제
      if (this.selectedChoice === choiceNumber) {
        this.selectedChoice = null;
        this.selectedContent = '';
      }
    }
    this.saveToLocalStorage();
  }

  // 확신도 설정
  setConfidenceLevel(level) {
    this.confidenceLevel = level; // low, medium, high
    this.saveToLocalStorage();
  }

  // 소요 시간 계산
  get elapsedTime() {
    const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  // 진행 상황 통계
  get stats() {
    return {
      hasSelection: this.selectedChoice !== null,
      eliminatedCount: this.eliminatedChoices.size,
      availableChoices: 30 - this.eliminatedChoices.size,
      confidenceLevel: this.confidenceLevel,
      elapsedTime: this.elapsedTime
    };
  }

  // 제출 준비 여부
  get canSubmit() {
    return this.selectedChoice !== null && !this.isSubmitted;
  }

  // 로컬 스토리지 저장
  saveToLocalStorage() {
    const state = {
      selectedChoice: this.selectedChoice,
      selectedContent: this.selectedContent,
      eliminatedChoices: Array.from(this.eliminatedChoices),
      confidenceLevel: this.confidenceLevel,
      startTime: this.startTime,
      tempSaveTime: Date.now()
    };
    localStorage.setItem('multiChoiceState', JSON.stringify(state));
  }

  // 로컬 스토리지에서 복원
  loadFromLocalStorage() {
    const saved = localStorage.getItem('multiChoiceState');
    if (saved) {
      const state = JSON.parse(saved);
      this.selectedChoice = state.selectedChoice;
      this.selectedContent = state.selectedContent;
      this.eliminatedChoices = new Set(state.eliminatedChoices);
      this.confidenceLevel = state.confidenceLevel;
      this.startTime = state.startTime;
      this.tempSaveTime = state.tempSaveTime;
    }
  }

  // 자동 저장 시작
  startAutoSave() {
    this.autoSaveInterval = setInterval(() => {
      this.saveToLocalStorage();
    }, 15000); // 15초마다 자동 저장
  }

  // 자동 저장 중지
  stopAutoSave() {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
    }
  }

  // 상태 초기화
  reset() {
    this.selectedChoice = null;
    this.selectedContent = '';
    this.eliminatedChoices.clear();
    this.confidenceLevel = 'medium';
    this.startTime = Date.now();
    this.tempSaveTime = null;
    this.isSubmitted = false;
    localStorage.removeItem('multiChoiceState');
  }
}

// 사용 예시
const multiChoiceState = new MultiChoiceState();

// Vue 컴포넌트에서 사용
export default {
  data() {
    return {
      state: multiChoiceState,
      choices: [] // API에서 로드된 30개 선택지
    }
  },
  
  mounted() {
    this.state.loadFromLocalStorage();
    this.state.startAutoSave();
    this.loadChoices();
  },
  
  beforeUnmount() {
    this.state.stopAutoSave();
  },
  
  computed: {
    currentStats() {
      return this.state.stats;
    },
    
    canSubmit() {
      return this.state.canSubmit;
    }
  },
  
  methods: {
    handleChoiceSelect(choice) {
      this.state.selectChoice(choice.number, choice.content);
    },
    
    handleToggleElimination(choiceNumber) {
      this.state.toggleElimination(choiceNumber);
    },
    
    handleConfidenceChange(level) {
      this.state.setConfidenceLevel(level);
    },
    
    async submitAnswer() {
      if (!this.canSubmit) return;
      
      const result = await this.submitToAPI({
        selected_choice: this.state.selectedChoice,
        selected_content: this.state.selectedContent,
        confidence_level: this.state.confidenceLevel,
        eliminated_choices: Array.from(this.state.eliminatedChoices),
        time_spent: Math.floor((Date.now() - this.state.startTime) / 1000)
      });
      
      this.state.isSubmitted = true;
      return result;
    }
  }
}
```

이제 완전히 새로운 형태의 **1문제 30선택지** 진단 테스트 UI가 완성되었습니다! 🎯

### 🌟 **주요 특징들**
- **1개 문제 + 30개 선택지**: 한 번에 모든 선택지를 비교 가능
- **선택지 제거 기능**: 확실히 틀린 것들을 제거하여 집중
- **확신도 표시**: 자신의 확신 정도를 함께 기록
- **실시간 타이머**: 문제 해결 시간 추적
- **스마트 필터링**: 선택된 것만/제외된 것만 보기 기능
- **더블클릭 제출**: 확신하면 바로 제출 가능

정말 흥미로운 형태의 진단 테스트네요! 이런 방식이면 사용자의 **선택 과정과 전략**까지 분석할 수 있겠습니다! 👍 