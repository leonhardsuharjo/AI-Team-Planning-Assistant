# SHIFTIQ Demo Walkthrough (90 seconds)

This walkthrough demonstrates the complete SHIFTIQ workflow from initial dashboard view to AI-powered schedule generation and conflict resolution.

## Prerequisites
- Application running at `http://localhost:5000`
- Database pre-seeded with 10 workers and coverage requirements

## Demo Script

### [0:00-0:15] Initial Dashboard View

**Action**: Open browser to `http://localhost:5000`

**What to observe**:
- Dashboard loads with SHIFTIQ logo and header
- Week label shows "Week of [current date]"
- Status badge displays "Acceptable" in amber
- Shift grid shows 7 days × 2 shifts (14 cells)
- Right sidebar shows "Workers" tab with 10 pre-seeded workers

**Key talking point**: "SHIFTIQ comes pre-loaded with 10 fictional workers across 3 roles—Cashier, Supervisor, and Technician—with realistic mixed availability patterns."

---

### [0:15-0:30] Identify Understaffed Shift

**Action**: Locate Friday Evening cell in the shift grid

**What to observe**:
- Friday Evening cell is colored **amber** (partial coverage)
- Cell displays "2/3" (2 workers assigned, 3 required)
- Small warning icon (!) appears in top-right corner of cell

**Key talking point**: "Notice Friday Evening is understaffed—only 2 workers available but we need 3. This is a pre-existing conflict in our seed data that demonstrates the AI's problem-solving capability."

---

### [0:30-0:45] Generate AI-Powered Schedule

**Action**: Click the blue "Generate Schedule" button in the header

**What to observe**:
- Button text changes to "Generating..."
- Button becomes disabled during processing
- IBM Granite 13B analyzes:
  - 10 workers × 7 days × 2 shifts = 140 availability data points
  - 14 coverage requirements (min/preferred workers per slot)
  - Detected conflicts (understaffed slots, role requirements)

**Key talking point**: "IBM Granite 13B is now analyzing worker availability, detecting conflicts, and generating an optimized schedule with natural-language reasoning. This takes just 2-3 seconds."

---

### [0:45-1:00] View Updated Schedule

**Action**: Observe the shift grid after generation completes

**What to observe**:
- Friday Evening cell now shows **green** (full coverage)
- Cell displays "3/3" (3 workers assigned, 3 required)
- Other cells update with color coding:
  - **Green**: Fully staffed (assigned ≥ required)
  - **Amber**: Partially staffed (assigned < required but > 0)
  - **Red**: No coverage (assigned = 0 but required > 0)
- Status badge may update to "Optimal" if all requirements met

**Key talking point**: "The schedule is now complete. Friday Evening is fully staffed with 3 workers. The color-coded grid lets managers see staffing status at a glance—green means we're good, amber means we're short, red means critical."

---

### [1:00-1:15] Read Granite's Conflict Resolution

**Action**: Click the "Conflicts" tab in the right sidebar

**What to observe**:
- Conflict cards appear showing detected issues
- Each card displays:
  - **Conflict type badge**: "UNDERSTAFFED" in amber
  - **Day and shift**: "Friday Evening"
  - **Description**: "Friday Evening needs 3 workers but only 2 available"
  - **Granite's Resolution** (collapsible section): Natural language explanation

**Example resolution text**:
> "Assigned Maria Rossi to Friday Evening despite her preference for morning shifts, as she was the only available Cashier meeting the role requirement. Recommended hiring one additional Evening Cashier to improve future coverage."

**Key talking point**: "This is the game-changer—Granite explains *why* it made each decision in plain English. Managers can read and trust the AI's reasoning instead of treating it as a black box."

---

### [1:15-1:30] Modify Worker Availability

**Action**: 
1. Click the "Workers" tab to return to worker list
2. Click on "Maria Rossi" worker card
3. Modal opens showing her details and 7-day availability grid
4. Toggle **Saturday Morning** from green (available) to grey (unavailable)
5. Click "Save Worker"

**What to observe**:
- Modal closes
- Worker card updates to show new availability pattern (one less green dot)
- Maria's total hours may decrease if she was previously assigned Saturday Morning

**Key talking point**: "Managers can update worker availability in real-time. Let's say Maria requests Saturday morning off—we just toggle it, save, and the system is ready to regenerate the schedule."

---

### [1:30-1:45] Regenerate Schedule

**Action**: Click "Generate Schedule" button again

**What to observe**:
- Schedule regenerates with Maria's updated availability
- Saturday Morning cell may change color if Maria was critical to that shift
- New conflicts may appear if Saturday Morning is now understaffed
- Granite provides new reasoning for the updated schedule

**Key talking point**: "The AI instantly adapts to the change. If Maria was assigned to Saturday Morning, Granite will reassign that shift to another available worker and explain the decision."

---

### [1:45-1:60] Explore Shift Details

**Action**: Click any shift cell in the grid (e.g., Monday Morning)

**What to observe**:
- Modal opens showing "Monday Morning" title
- **Assignment list** displays all workers assigned to that shift:
  - Worker name
  - Role (Cashier, Supervisor, Technician)
- If conflicts exist for this shift, they appear below with Granite's resolution

**Key talking point**: "Clicking any cell shows exactly who's working that shift. This drill-down view helps managers verify assignments and understand the AI's decisions at a granular level."

---

### [1:60-1:75] Review Worker Hours

**Action**: Scroll through the Workers tab in the sidebar

**What to observe**:
- Each worker card shows:
  - Name and role
  - **Total hours this week** (e.g., "32h this week")
  - 14 availability dots (7 days × 2 shifts)
    - Green dot = available
    - Grey dot = unavailable

**Key talking point**: "The system tracks each worker's total hours to prevent over-scheduling. If someone is approaching their max hours per week, Granite factors that into future assignments."

---

### [1:75-1:90] Highlight Key Benefits

**Action**: Summarize the demo

**Key talking points**:
1. **Time Savings**: "What used to take 60+ minutes of manual work now takes under 2 minutes."
2. **Conflict Prevention**: "The AI detects and resolves conflicts before they impact operations."
3. **Transparency**: "Natural-language reasoning builds manager trust—they understand why each decision was made."
4. **Adaptability**: "Real-time updates let managers adjust to last-minute changes instantly."
5. **Reliability**: "If the watsonx API is unavailable, the system falls back to rule-based scheduling—no crashes, always generates a schedule."

---

## Advanced Demo Features (Optional)

### Fallback Mode Demonstration
1. Stop the watsonx API connection (remove API key from `.env`)
2. Restart the application
3. Click "Generate Schedule"
4. Observe: Schedule still generates using rule-based logic
5. Conflicts panel shows "Fallback Mode" badge
6. Resolution text reads: "Rule-based assignment - watsonx unavailable"

### Add New Worker
1. Click "+ Add Worker" button
2. Fill in: Name="John Smith", Role="Cashier", Max Hours=35
3. Toggle availability for Monday-Friday Morning shifts
4. Click "Save Worker"
5. Regenerate schedule to see John included in assignments

### Confirm Schedule
1. After generating a satisfactory schedule, click "Confirm Schedule" (if implemented)
2. Status changes from "DRAFT" to "CONFIRMED"
3. Schedule is locked and ready for distribution to workers

---

## Demo Tips

- **Pace yourself**: Each section should take exactly 15 seconds
- **Highlight colors**: Point out the green/amber/red color coding frequently
- **Read Granite's reasoning aloud**: This is the most impressive feature
- **Show the dots**: The availability dot indicators are intuitive and visual
- **Emphasize speed**: Mention "2 minutes vs 60 minutes" multiple times

## Common Questions & Answers

**Q: What if a worker calls in sick?**  
A: Mark them unavailable for that day, regenerate the schedule, and Granite will reassign their shifts.

**Q: Can it handle night shifts?**  
A: Yes, the system supports Morning/Evening/Night shifts. The demo uses Morning/Evening for simplicity.

**Q: Does it work offline?**  
A: The application runs fully locally. Only the IBM Granite API call requires internet. If offline, it uses rule-based fallback.

**Q: How does it handle role requirements?**  
A: Coverage requirements can specify "Cashier required" for certain shifts. Granite respects these constraints.

**Q: Can workers see their own schedules?**  
A: The current version is manager-focused. A worker portal would be a natural next feature.

---

## Success Metrics

After the demo, the audience should understand:
- ✅ The problem: Manual scheduling wastes time and creates conflicts
- ✅ The solution: AI-powered scheduling with natural language reasoning
- ✅ The technology: IBM Granite 13B via watsonx.ai
- ✅ The impact: 97% time savings, <2% conflict rate
- ✅ The trust factor: Transparent AI decisions managers can read and verify
