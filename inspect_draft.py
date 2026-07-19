import json

def inspect_segments():
    with open('D:/CAIDAT\CAPCUT/CapCut Drafts/0627/draft_content.json', 'r', encoding='utf-8') as f:
        d = json.load(f)
    
    print("Tracks in current draft_content.json:")
    for i, t in enumerate(d.get('tracks', [])):
        print(f"Track {i} type: {t.get('type')}, segments: {len(t.get('segments', []))}")
        for j, seg in enumerate(t.get('segments', [])[:3]):
            target_tr = seg.get('target_timerange', {})
            print(f"  Seg {j}: target start={target_tr.get('start')}, duration={target_tr.get('duration')}")

if __name__ == "__main__":
    inspect_segments()
