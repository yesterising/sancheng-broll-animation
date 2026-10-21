#!/usr/bin/env python3
"""Extract an unedited SRT timing scaffold; semantic design belongs to the agent."""
import argparse
import json
import re
import sys
from fractions import Fraction
from pathlib import Path


STAMP = r"\d{2,}:\d{2}:\d{2}[,.]\d{3}"
TIMING = re.compile(rf"^({STAMP})\s*-->\s*({STAMP})(?:\s+.*)?$")


def milliseconds(stamp):
    h, m, s, ms = map(int, re.split(r"[:,.]", stamp))
    if m >= 60 or s >= 60:
        raise ValueError(f"Invalid timestamp: {stamp}")
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def ceil_fraction(value):
    return -(-value.numerator // value.denominator)


def build_timeline(content, fps, duration=None):
    if fps <= 0:
        raise ValueError("fps must be positive")
    cues, warnings = [], []
    content = content.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip('\n')
    blocks = re.split(r"\n[ \t]*\n", content) if content.strip() else []
    for position, block in enumerate(blocks, 1):
        lines = block.splitlines()
        timing_index = 1 if lines[0].strip().isdigit() else 0
        match = TIMING.fullmatch(lines[timing_index].strip()) if len(lines) > timing_index else None
        if not match or len(lines) <= timing_index + 1:
            raise ValueError(f"Malformed or empty SRT cue at block {position}")
        start, end = (milliseconds(x) for x in match.groups())
        if end <= start:
            raise ValueError(f"Cue {position} ends before or at its start")
        if cues and start < cues[-1]['start_ms']:
            raise ValueError(f"Cue {position} is out of chronological order; source was not reordered")
        cues.append({
            'position': position,
            'source_id': lines[0].strip() if timing_index else None,
            'start_ms': start, 'end_ms': end,
            'start': start / 1000, 'end': end / 1000,
            'text': '\n'.join(lines[timing_index + 1:]),
            'frame_start_inclusive': (Fraction(start, 1000) * fps).__floor__(),
            'frame_end_exclusive': ceil_fraction(Fraction(end, 1000) * fps),
        })
    if not cues:
        raise ValueError('No SRT cues found')
    narration_end = max(cue['end_ms'] for cue in cues)
    total = Fraction(narration_end, 1000) if duration is None else Fraction(duration)
    if total < Fraction(narration_end, 1000):
        raise ValueError('SRT extends beyond the supplied final timeline duration; resolve the mismatch')
    gaps, covered_until = [], 0
    for cue in cues:
        if cue['start_ms'] > covered_until:
            gaps.append({'start': covered_until / 1000, 'end': cue['start']})
        elif cue['start_ms'] < covered_until:
            warnings.append(f"Cue {cue['position']} overlaps preceding subtitle coverage; original times kept")
        covered_until = max(covered_until, cue['end_ms'])
    if total > Fraction(covered_until, 1000):
        gaps.append({'start': covered_until / 1000, 'end': float(total)})
    frames = ceil_fraction(total * fps)
    if duration is None:
        warnings.append('Duration is estimated from the last subtitle, not confirmed final project duration')
    return {
        'design_status': 'timing_scaffold_needs_semantic_storyboard',
        'fps': str(fps), 'duration': float(total),
        'duration_is_estimate': duration is None,
        'narration_end': narration_end / 1000,
        'frame_count': frames, 'render_duration': float(Fraction(frames, 1) / fps),
        'cue_count': len(cues), 'cues': cues,
        'subtitle_gaps_need_visual_design': gaps, 'warnings': warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('srt', type=Path)
    parser.add_argument('--fps', required=True, help='Actual project rate, e.g. 30 or 30000/1001')
    parser.add_argument('--duration', help='Final project duration in seconds; omission means estimate')
    parser.add_argument('--encoding', default='utf-8-sig')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build_timeline(args.srt.read_text(encoding=args.encoding), Fraction(args.fps), args.duration)
        result['source_srt'] = str(args.srt.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as target:
            json.dump(result, target, ensure_ascii=False, indent=2)
            target.write('\n')
    except (OSError, ValueError, ZeroDivisionError) as error:
        parser.exit(1, f'Error: {error}\n')
    print(json.dumps({'output': str(args.output.resolve()), 'cue_count': result['cue_count'],
                      'duration_is_estimate': result['duration_is_estimate'],
                      'warnings': result['warnings']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
