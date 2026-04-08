# Custom Dashboard Testing Guide

## Quick 5-Minute Test

### Test 1: System Health ✓
1. Open http://localhost:8000
2. Verify page loads without errors
3. All buttons visible and clickable
4. API status shows "Ready"

### Test 2: Domain Selection ✓
1. Click Bridge Truss → highlight changes
2. Click Pressure Vessel → highlight changes
3. Click Gear Assembly → highlight changes
4. Click Building Frame → highlight changes

### Test 3: Difficulty Selection ✓
1. Click Easy → button highlights orange
2. Click Medium → button highlights orange
3. Click Hard → button highlights orange

### Test 4: Generate Design ✓
1. Bridge Truss, Medium, Seed 42
2. Click "Generate New Design"
3. Verify response:
   - Design ID appears
   - Component count shows
   - Flaws count shows
   - Summary text appears

### Test 5: Run Expert Agent ✓
1. Keep same domain/difficulty/seed
2. Click "Run Expert Agent"
3. Watch progression:
   - Phase 1: Component inspection
   - Phase 2: Physics analysis
   - Phase 3: Issue flagging
   - Phase 4: Final decision
4. Verify composite score updated

### Test 6: Different Domain ✓
1. Select Pressure Vessel, Hard, Seed 100
2. Click "Generate New Design"
3. Click "Run Expert Agent"
4. Verify different components/flaws

### Test 7: Scoring System ✓
1. After agent completes:
   - Detection Precision % changes
   - Detection Recall % changes
   - Efficiency score updates
   - Composite score shown
   - Reward displayed

---

## Expected Results

| Test | Should See | Status |
|------|-----------|--------|
| Domain buttons | Color highlights | ✓ |
| New design | Design ID + components | ✓ |
| Physics analysis | Stress/safety factors | ✓ |
| Expert agent | 4-phase workflow | ✓ |
| Scoring | 6 dimensions + composite | ✓ |
| Different seeds | Unique designs | ✓ |
| Difficulty levels | Varying complexity | ✓ |

---

## Troubleshooting

### Issue: Page doesn't load
- Check server running: `http://localhost:8000/health`
- Check terminal for errors

### Issue: Buttons don't respond
- Open browser console (F12)
- Check JavaScript errors
- Verify API endpoints active

### Issue: "Generate Design" takes >5 seconds
- Normal if many components
- Check network tab for hanging requests

### Issue: Score always 0
- Run complete agent workflow
- Verify final decision made
- Check if reward calculated

---

## Performance Baselines

| Domain | Components | Flaws | Agent Time |
|--------|-----------|-------|-----------|
| Bridge Truss | 7-8 | 2-3 | ~3-5s |
| Pressure Vessel | 6-7 | 2-4 | ~4-6s |
| Gear Assembly | 6 | 1-2 | ~2-3s |
| Building Frame | 8-10 | 3-4 | ~5-7s |

