# Frequency Band Reference - NYC Metro

Common frequencies for the New York City metropolitan area (Manhattan, Hoboken, Weehawken, Jersey City).

## FM Broadcast (87.5-108 MHz)

Major NYC FM stations:

| Frequency | Call Sign | Format | Notes |
|-----------|-----------|--------|-------|
| 88.3 MHz | WBGO | Jazz | Newark-based, strong in Hoboken |
| 89.9 MHz | WKCR | Variety | Columbia University |
| 91.5 MHz | WNYE | Public | NYC-owned |
| 93.9 MHz | WNYC-FM | Public Radio | NPR affiliate |
| 95.5 MHz | WPLJ | Hot AC | NYC classic |
| 97.1 MHz | WQHT | Hip-Hop | Hot 97 |
| 98.7 MHz | WRKS | Urban | Kiss FM |
| 100.3 MHz | WHTZ | Top 40 | Z100 |
| 101.9 MHz | WFAN-FM | Sports | Very strong signal |
| 103.5 MHz | WKTU | Dance | |
| 104.3 MHz | WAXQ | Classic Rock | Q104.3 |
| 105.1 MHz | WWPR | Hip-Hop | Power 105.1 |
| 106.7 MHz | WLTW | Adult Contemporary | Lite FM |
| 107.5 MHz | WBLS | Urban | |

### Scan Command
```python
scanner.scan(87.5e6, 108.0e6, step_hz=200e3)
```

## NOAA Weather Radio (162.40-162.55 MHz)

| Frequency | Station | Coverage |
|-----------|---------|----------|
| 162.55 MHz | WXK52 | NYC metro primary |
| 162.475 MHz | WXL51 | Backup coverage |
| 162.40 MHz | KHB31 | NJ coverage |

### Listen Command
```bash
rfad-fm -f 162.55
```

## Amateur Radio 2m Band (144-148 MHz)

NYC area repeaters:

| Frequency | Call Sign | Location | Notes |
|-----------|-----------|----------|-------|
| 146.955 MHz | W2LI | Long Island | -600 kHz offset |
| 147.000 MHz | N2YGK | Manhattan | +600 kHz offset |
| 146.61 MHz | N2LEN | Bergen County | |
| 147.045 MHz | K2RVW | Westchester | |

### Scan Command
```python
scanner.scan(144.0e6, 148.0e6, step_hz=12.5e3)
```

**Note:** Amateur transmission requires license. Reception is legal.

## Aircraft Band (118-137 MHz)

NYC area airports and approaches:

| Frequency | Facility | Purpose |
|-----------|----------|---------|
| 118.3 MHz | EWR Tower | Newark Liberty |
| 118.7 MHz | LGA Tower | LaGuardia |
| 119.1 MHz | JFK Tower | JFK International |
| 119.5 MHz | TEB Tower | Teterboro (private jets) |
| 121.5 MHz | Emergency | Guard frequency |
| 123.9 MHz | NY TRACON | Approach control |
| 125.95 MHz | NY Center | En-route |
| 128.4 MHz | JFK Ground | Ground control |
| 134.1 MHz | ATIS | Weather info |

### Scan Command
```python
scanner.scan(118.0e6, 137.0e6, step_hz=25e3)
```

**Note:** Aircraft use AM modulation, not FM. Toolkit defaults to FM; AM mode requires modification.

## Marine VHF (156-162 MHz)

Hudson River and NY Harbor:

| Channel | Frequency | Purpose |
|---------|-----------|---------|
| 16 | 156.8 MHz | Distress/calling |
| 13 | 156.65 MHz | Bridge-to-bridge |
| 12 | 156.6 MHz | Port operations |
| 14 | 156.7 MHz | Port operations |
| 22A | 157.1 MHz | Coast Guard |
| 68 | 156.425 MHz | Marina operations |
| 72 | 156.625 MHz | Ship-to-ship |

### Scan Command
```python
scanner.scan(156.0e6, 162.0e6, step_hz=25e3)
```

## FRS/GMRS (462-467 MHz)

Family Radio Service / General Mobile Radio Service:

| Channel | Frequency | Notes |
|---------|-----------|-------|
| 1 | 462.5625 MHz | FRS/GMRS shared |
| 8 | 467.5625 MHz | FRS only |
| 15 | 462.550 MHz | GMRS only |

### Scan Command
```python
scanner.scan(462.0e6, 467.0e6, step_hz=12.5e3)
```

## MURS (151-154 MHz)

Multi-Use Radio Service (license-free):

| Channel | Frequency |
|---------|-----------|
| 1 | 151.82 MHz |
| 2 | 151.88 MHz |
| 3 | 151.94 MHz |
| 4 | 154.57 MHz |
| 5 | 154.60 MHz |

## Summary Table

| Band | Frequency Range | Step Size | Modulation |
|------|-----------------|-----------|------------|
| FM Broadcast | 87.5-108 MHz | 200 kHz | WFM |
| NOAA Weather | 162.4-162.55 MHz | 25 kHz | NFM |
| Amateur 2m | 144-148 MHz | 12.5 kHz | NFM |
| Aircraft | 118-137 MHz | 25 kHz | AM |
| Marine VHF | 156-162 MHz | 25 kHz | NFM |
| FRS/GMRS | 462-467 MHz | 12.5 kHz | NFM |

## RTL-SDR Frequency Range

The RTL-SDR (R820T tuner) covers:
- **Minimum:** ~24 MHz
- **Maximum:** ~1766 MHz
- **Sweet spot:** 50-1000 MHz

Frequencies outside this range require upconverter (HF) or different hardware.
