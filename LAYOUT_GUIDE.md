# 📐 New Layout Guide - SENSE Flow

## Application Window Structure

```
╔════════════════════════════════════════════════════════════════════╗
║                          SENSE Flow                                ║
╠═══════════════╦════════════════════════════╦═══════════════════════╣
║               ║                            ║                       ║
║  Connection   ║  🔧 Direct Flow Control    ║  📊 Real-time         ║
║  & Control    ║         [⏹ Stop All]       ║     Monitoring        ║
║               ║ ─────────────────────────── ║                       ║
║  🔌 Connect   ║                            ║  ┌─────────────────┐  ║
║  Port: [▼]    ║  ╔══ Base gas (air) ══╗    ║  │  Base Gas Flow  │  ║
║  [🔍 Scan]    ║  ║  📊 Range: ...     ║    ║  │                 │  ║
║               ║  ║  🎯 Set: [__] [✓][⏹]║   ║  │   (graph 1)     │  ║
║  ⚗️ Conc.     ║  ║  💨 Flow: [___]    ║    ║  │                 │  ║
║  Control      ║  ║  🔧 Valve: [__]    ║    ║  └─────────────────┘  ║
║               ║  ║  🌡️ Temp: [___]    ║    ║                       ║
║  Base: 20     ║  ╚════════════════════╝    ║  ┌─────────────────┐  ║
║  Var: [▼]     ║                            ║  │Variable Gas Flow│  ║
║  ─────────    ║  ╔══ High flow ══════╗    ║  │                 │  ║
║  C_tot: [_]   ║  ║  📊 Range: ...     ║    ║  │   (graph 2)     │  ║
║  C1:    [_]   ║  ║  🎯 Set: [__] [✓][⏹]║   ║  │                 │  ║
║  C2:    [_]   ║  ║  💨 Flow: [___]    ║    ║  └─────────────────┘  ║
║  Max:   [_]   ║  ║  🔧 Valve: [__]    ║    ║                       ║
║               ║  ║  🌡️ Temp: [___]    ║    ║  ┌─────────────────┐  ║
║  [⚡ Calc]    ║  ╚════════════════════╝    ║  │ Concentration   │  ║
║               ║                            ║  │                 │  ║
║               ║  (scrollable area)         ║  │   (graph 3)     │  ║
║               ║                            ║  │                 │  ║
║               ║                            ║  └─────────────────┘  ║
╠═══════════════╩════════════════════════════╩═══════════════════════╣
║  📋 System Log                                                     ║
║  [12:34:56] ℹ️ Scanning for instruments...                        ║
║  [12:34:57] ✓ Found instruments at addresses: [3, 5, 8, 20]      ║
║  [12:34:58] ✓ Connected to 4 instruments                          ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## Key Layout Features

### Left Panel (Fixed Width)
- **Connection Panel** 🔌
  - COM port selection
  - Scan button
- **Concentration Control** ⚗️
  - Gas assignments
  - Concentration parameters
  - Calculate button

### Center Panel (Flexible Width)
- **Header Bar**
  - Title: "🔧 Direct Flow Control"
  - **⏹ Stop All Flows** button (top-right)
- **Scrollable Instrument List**
  - White background (clean!)
  - Card-style instruments
  - Each with **Stop** button

### Right Panel (Flexible Width)
- **Real-time Monitoring** 📊
- **3 Graphs Stacked Vertically:**
  1. Base Gas Flow (top)
  2. Variable Gas Flow (middle)
  3. Concentration (bottom)

### Bottom Panel (Fixed Height)
- **System Log** 📋
  - Color-coded messages
  - Scrollable output

---

## Instrument Card Detail

```
╔════════════════════════════════════════════════╗
║  Low flow                              [8]     ║  ← Header with name & address
║  ───────────────────────────────────────────   ║  ← Separator
║  📊 Range: 0.1360 - 10.00 mln/min             ║  ← Flow range info
║                                                ║
║  🎯 Set Flow: [_______] mln/min               ║  ← Input field
║                    [✓ Apply]  [⏹ Stop]        ║  ← Action buttons
║                    (green)    (orange)         ║
║                                                ║
║  💨 Flow:       ┌─────────┐  mln/min          ║  ← Live reading
║                 │  2.450  │                    ║
║                 └─────────┘                    ║
║  🔧 Valve:      ┌─────────┐  %                ║  ← Valve position
║                 │  45.2   │                    ║
║                 └─────────┘                    ║
║  🌡️ Temperature: ┌─────────┐  °C              ║  ← Temperature
║                 │  22.3   │                    ║
║                 └─────────┘                    ║
╚════════════════════════════════════════════════╝
```

---

## Button Placement Guide

### Global Buttons

**Top-Right of Flow Control Panel:**
```
┌────────────────────────────────────────┐
│ 🔧 Direct Flow Control  [⏹ Stop All]  │
│                         └─────────────┘│
│                         Always visible │
└────────────────────────────────────────┘
```

### Per-Instrument Buttons

**In Each Instrument Card:**
```
🎯 Set Flow: [12.5] mln/min  [✓ Apply]  [⏹ Stop]
                             └───────┘  └────────┘
                             Set the    Set to 0
                             value      immediately
```

---

## Graph Orientation

### Old Layout (Horizontal)
```
┌────────┬────────┬─────────────┐
│ Flow 1 │ Flow 2 │ Conc.       │
│        │        │             │
└────────┴────────┴─────────────┘
```
- Graphs were small
- Hard to see details
- Limited vertical space usage

### New Layout (Vertical)
```
┌───────────────────┐
│   Base Gas Flow   │
│  (larger graph)   │
├───────────────────┤
│ Variable Gas Flow │
│  (larger graph)   │
├───────────────────┤
│  Concentration    │
│  (larger graph)   │
└───────────────────┘
```
- Graphs are larger
- Better use of screen space
- Easier to read trends
- Time axis aligned

---

## Color Scheme Reference

### Panel Backgrounds
- **Left Panel:** White card on light gray
- **Center Panel:** **WHITE** (improved!)
- **Right Panel:** White with graphs
- **Bottom Panel:** Light gray card

### Button Colors
- **🔍 Scan:** Blue (#3498DB)
- **⚡ Calculate:** Green (#27AE60)
- **✓ Apply:** Green (#27AE60)
- **⏹ Stop:** Orange (#F39C12)
- **⏹ Stop All:** Orange (#F39C12)

### Graph Colors
- **Flow 1:** Blue (#3498DB)
- **Flow 2:** Green (#2ECC71)
- **Actual Conc:** Blue (#3498DB)
- **Target Conc:** Red (#E74C3C)

---

## Responsive Behavior

### Window Resizing
- **Left Panel:** Fixed width (~250-300px)
- **Center Panel:** Expands with window
- **Right Panel:** Expands with window (2x center)
- **Bottom Panel:** Fixed height (~150px)

### Scrolling
- **Center Panel:** Vertical scroll for instruments
- **System Log:** Auto-scroll to newest messages
- **Graphs:** Fixed in place, no scroll

---

## User Actions Flow

### Starting a Flow
1. Enter value in instrument's input field
2. Click **✓ Apply** (green button)
3. Flow starts, monitor in graph

### Stopping Flows

**Option 1 - Single Instrument:**
```
Click [⏹ Stop] next to instrument
  ↓
Flow set to 0 for that instrument
  ↓
Entry field shows "0.0"
```

**Option 2 - All Instruments:**
```
Click [⏹ Stop All Flows] at top
  ↓
All flows set to 0
  ↓
Emergency stop complete
```

### Calculating Concentrations
1. Set concentration parameters (left panel)
2. Click **⚡ Calculate Flows**
3. Values appear in instrument fields
4. Click **✓ Apply** to start

---

## Space Utilization

### Before
- 30% graph area
- 40% controls
- 30% wasted space

### After
- 50% graph area (vertical stack)
- 40% controls
- 10% optimized spacing

**Result:** Better use of screen real estate! 📐

---

**New layout provides better visibility, easier control, and professional appearance! 🎨**
