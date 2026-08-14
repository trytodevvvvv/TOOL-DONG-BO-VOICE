#!/usr/bin/env python3
import os
import sys
import json
import argparse
import shutil
import subprocess
import re

try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

try:
    from pyJianYingDraft import ScriptFile, TrackType, VideoMaterial, AudioMaterial, VideoSegment, AudioSegment, Timerange
except ImportError:
    print("Error: Thư viện 'pyJianYingDraft' chưa được cài đặt. Vui lòng cài đặt bằng: pip install pyJianYingDraft")
    sys.exit(1)

def parse_srt_time(time_str):
    time_str = str(time_str).strip().replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return float(time_str)

def load_srt_sentences(srt_file_path):
    with open(srt_file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()

    # Match standard SRT subtitle blocks
    pattern = r'(?m)^\d+\s*\r?\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\r?\n([\s\S]*?)(?=\r?\n\r?\n\d+|\r?\n\r?\n*$|\Z)'
    matches = re.findall(pattern, content)

    sentences = []
    if matches:
        for m in matches:
            start_s = parse_srt_time(m[0])
            end_s = parse_srt_time(m[1])
            text = m[2].strip()
            sentences.append({
                "start": start_s,
                "end": end_s,
                "text": text
            })
    else:
        # Fallback block parsing
        blocks = re.split(r'\n\s*\n', content)
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if len(lines) >= 2:
                for i, line in enumerate(lines):
                    if '-->' in line:
                        times = line.split('-->')
                        start_s = parse_srt_time(times[0])
                        end_s = parse_srt_time(times[1])
                        text = " ".join(lines[i+1:])
                        sentences.append({
                            "start": start_s,
                            "end": end_s,
                            "text": text
                        })
                        break
    return sentences

def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def get_media_duration(file_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ffprobe = os.path.join(script_dir, "ffprobe.exe")
    ffprobe_cmd = local_ffprobe if os.path.exists(local_ffprobe) else "ffprobe"

    cmd = [
        ffprobe_cmd,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except ValueError:
            raise RuntimeError(f"Could not parse duration: {result.stdout}")
    else:
        raise RuntimeError(f"{ffprobe_cmd} failed: {result.stderr.strip()}")

def main():
    parser = argparse.ArgumentParser(description="Đồng bộ timeline CapCut từ file SRT Subtitles")
    parser.add_argument("--drafts-dir", required=True, help="Đường dẫn thư mục chứa các project CapCut")
    parser.add_argument("--project-name", required=True, help="Tên project (tên thư mục con)")
    parser.add_argument("--timestamps", required=True, help="Đường dẫn file SRT timestamp")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in kế hoạch thay đổi, không ghi file")

    args = parser.parse_args()

    project_dir = os.path.join(args.drafts_dir, args.project_name)
    
    # Check if the project uses the new Timelines structure (CapCut 5.x+)
    timelines_dir = os.path.join(project_dir, "Timelines")
    draft_content_path = None
    active_timeline_dir = None
    
    if os.path.exists(timelines_dir):
        project_json_path = os.path.join(timelines_dir, "project.json")
        if os.path.exists(project_json_path):
            try:
                with open(project_json_path, "r", encoding="utf-8") as f:
                    proj_data = json.load(f)
                main_id = proj_data.get("main_timeline_id") or proj_data.get("timelines", [{}])[0].get("id")
                if main_id:
                    candidate_dir = os.path.join(timelines_dir, main_id)
                    candidate_file = os.path.join(candidate_dir, "draft_content.json")
                    if os.path.exists(candidate_file):
                        draft_content_path = candidate_file
                        active_timeline_dir = candidate_dir
            except Exception:
                pass
        
        if not draft_content_path:
            for item in os.listdir(timelines_dir):
                item_path = os.path.join(timelines_dir, item)
                if os.path.isdir(item_path):
                    candidate_file = os.path.join(item_path, "draft_content.json")
                    if os.path.exists(candidate_file):
                        draft_content_path = candidate_file
                        active_timeline_dir = item_path
                        break
                        
    if not draft_content_path:
        draft_content_path = os.path.join(project_dir, "draft_content.json")
        active_timeline_dir = project_dir

    if not os.path.exists(draft_content_path):
        print(f"Error: Không tìm thấy file draft_content.json tại: {draft_content_path}")
        sys.exit(1)

    # 1. VALIDATE draft_content.json
    try:
        with open(draft_content_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            json.loads(raw_content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("Error: file này không đọc được dạng text, cần hướng xử lý khác")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Không thể đọc file draft_content.json: {e}")
        sys.exit(1)

    # 2. LOAD TIMESTAMPS FROM SRT
    if not os.path.exists(args.timestamps):
        print(f"Error: Không tìm thấy file timestamps tại: {args.timestamps}")
        sys.exit(1)

    try:
        sentences = load_srt_sentences(args.timestamps)
    except Exception as e:
        print(f"Error: Không thể phân tích cú pháp file SRT: {e}")
        sys.exit(1)

    if not sentences:
        print("Error: File SRT không chứa mốc thời gian phụ đề hợp lệ nào.")
        sys.exit(1)

    # Auto-detect audio file
    voice_file = None
    base_path = os.path.splitext(args.timestamps)[0]
    for ext in [".mp3", ".wav", ".m4a", ".mp4", ".MP3", ".WAV", ".M4A", ".MP4"]:
        candidate = base_path + ext
        if os.path.exists(candidate):
            voice_file = candidate
            break

    if not voice_file:
        try:
            script_temp = ScriptFile.load_template(draft_content_path)
            imported_audios = script_temp.imported_materials.get("audios", [])
            if imported_audios:
                voice_file = imported_audios[0].get("path")
        except Exception:
            pass

    if not voice_file:
        print("Error: Không xác định được file voice/audio.")
        sys.exit(1)

    # 3. LOAD PROJECT VIA pyJianYingDraft
    try:
        script = ScriptFile.load_template(draft_content_path)
    except Exception as e:
        print(f"Error: Không thể load draft bằng pyJianYingDraft: {e}")
        sys.exit(1)

    imported_videos = script.imported_materials.get("videos", [])
    imported_videos.sort(key=lambda m: os.path.basename(m.get("path") or "").lower())

    visuals_list = []
    for idx, sent in enumerate(sentences):
        start = float(sent.get("start", 0.0))
        end = float(sent.get("end", 0.0))
        
        if idx < len(imported_videos):
            matched_mat = imported_videos[idx]
            v_path = matched_mat.get("path") or ""
            matched_filename = os.path.basename(v_path)
            ext = os.path.splitext(matched_filename)[1].lower()
            v_type = "video" if ext in (".mp4", ".mkv", ".mov", ".avi") else "image"
            visuals_list.append({
                "type": v_type,
                "file": matched_filename,
                "material": matched_mat,
                "start": start,
                "end": end
            })
        else:
            print(f"Warning: Số lượng timeline trong file SRT nhiều hơn số lượng ảnh/video đã nhập (thiếu ảnh cho mốc thứ {idx+1}).")

    if not visuals_list:
        print("Error: Không có visual segment nào từ project khớp với file SRT.")
        sys.exit(1)

    # 4. MATCH MATERIALS
    imported_audios = script.imported_materials.get("audios", [])
    voice_mat = None
    voice_filename = os.path.basename(voice_file).lower()
    for mat in imported_audios:
        path = mat.get("path") or ""
        if os.path.basename(path).lower() == voice_filename:
            voice_mat = mat
            break

    warnings_count = 0

    if not voice_mat:
        if os.path.exists(voice_file):
            voice_path = os.path.abspath(voice_file)
        else:
            print(f"Warning: Không tìm thấy file voice '{voice_file}' trong dự án hoặc ổ đĩa.")
            sys.exit(1)
    else:
        voice_path = voice_mat.get("path")

    try:
        voice_duration = get_media_duration(voice_path)
    except Exception as e:
        print(f"Error: Không thể đo độ dài file voice: {e}")
        sys.exit(1)

    matched_visuals = []
    for idx, visual in enumerate(visuals_list):
        v_file = visual.get("file") or visual.get("path")
        v_type = visual.get("type", "image")
        start = float(visual.get("start", 0.0))
        end = float(visual.get("end", 0.0))

        if not v_file:
            print(f"Warning: Clip thứ {idx+1} trong SRT thiếu thông tin file.")
            warnings_count += 1
            continue

        matched_mat = visual.get("material")
        if not matched_mat:
            filename_lower = os.path.basename(v_file).lower()
            for mat in imported_videos:
                path = mat.get("path") or ""
                if os.path.basename(path).lower() == filename_lower:
                    matched_mat = mat
                    break

        if not matched_mat:
            print(f"Warning: Không tìm thấy file visual '{v_file}' trong project materials.")
            warnings_count += 1
            continue

        matched_visuals.append({
            "material": matched_mat,
            "type": v_type,
            "file": v_file,
            "start": start,
            "end": end
        })

    if not matched_visuals:
        print("Error: Không khớp được visual segment nào từ project.")
        sys.exit(1)

    # Đảm bảo các đoạn ảnh/video nối tiếp nhau không kẽ hở
    current_time = 0.0
    for idx, item in enumerate(matched_visuals):
        item["start"] = current_time
        if item["end"] <= item["start"]:
            item["end"] = item["start"] + 1.0
        current_time = item["end"]

    # 5. ADJUST LAST SEGMENT DURATION
    last_visual = matched_visuals[-1]
    total_visuals_end = last_visual["end"]
    discrepancy = total_visuals_end - voice_duration
    abs_discrepancy = abs(discrepancy)
    adjustment_made = 0.0

    if abs_discrepancy > 0.001:
        if abs_discrepancy > 2.0:
            print(f"Warning: chênh lệch lớn ({abs_discrepancy:.2f} giây), kiểm tra lại timestamp.")
            warnings_count += 1

        new_end = voice_duration
        new_duration = new_end - last_visual["start"]

        if discrepancy < 0:
            if last_visual["type"] == "video":
                video_path = last_visual["material"].get("path")
                try:
                    orig_dur = get_media_duration(video_path)
                except Exception:
                    orig_dur = float(last_visual["material"].get("duration", 0)) / 1e6

                if new_duration > orig_dur:
                    print(f"CẢNH BÁO RIÊNG: Video segment cuối cùng '{last_visual['file']}' không thể tự kéo dài vượt quá độ dài gốc ({orig_dur:.2f}s).")
                    warnings_count += 1
                else:
                    last_visual["end"] = new_end
                    adjustment_made = new_end - total_visuals_end
            else:
                last_visual["end"] = new_end
                adjustment_made = new_end - total_visuals_end
        else:
            last_visual["end"] = new_end
            adjustment_made = new_end - total_visuals_end

    # 6. IN KẾ HOẠCH NẾU DRY-RUN
    if args.dry_run:
        print("\n=== KẾ HOẠCH ĐỒNG BỘ TIMELINE (DRY-RUN SRT) ===")
        print(f"{'File Name':<35} | {'Track':<15} | {'Start (s)':<10} | {'End (s)':<10} | {'Type':<8}")
        print("-" * 85)
        print(f"{os.path.basename(voice_path):<35} | {'Voice Track':<15} | {0.0:<10.2f} | {voice_duration:<10.2f} | {'audio':<8}")
        for item in matched_visuals:
            print(f"{os.path.basename(item['file']):<35} | {'Visual Track':<15} | {item['start']:<10.2f} | {item['end']:<10.2f} | {item['type']:<8}")
        print("-" * 85)
        print(f"Tổng kết dry-run SRT: {len(matched_visuals)} visual segments, chênh lệch điều chỉnh: {adjustment_made:.2f}s, warnings: {warnings_count}")
        sys.exit(0)

    # 7. REBUILD TRACKS
    voice_mat_id = voice_mat.get("id") or voice_mat.get("material_id") if voice_mat else None
    
    visual_mat_ids = set()
    for item in matched_visuals:
        mat_id = item["material"].get("id") or item["material"].get("material_id")
        if mat_id:
            visual_mat_ids.add(mat_id)

    retained_imported_tracks = []
    for t in script.imported_tracks:
        is_tool_track = False
        
        if isinstance(t, dict):
            name = t.get("name", "")
            segments = t.get("segments", [])
        else:
            name = getattr(t, "name", "") or (getattr(t, "raw_data", {}).get("name", "") if hasattr(t, "raw_data") else "")
            segments = getattr(t, "segments", [])
            
        if name in ["Voice Track", "Visual Track"]:
            is_tool_track = True
            
        if not is_tool_track:
            for seg in segments:
                if isinstance(seg, dict):
                    mat_id = seg.get("material_id")
                else:
                    mat_id = getattr(seg, "material_id", None) or (getattr(seg, "raw_data", {}).get("material_id") if hasattr(seg, "raw_data") else None)

                if mat_id:
                    if voice_mat_id and mat_id == voice_mat_id:
                        is_tool_track = True
                        break
                    if mat_id in visual_mat_ids:
                        is_tool_track = True
                        break
                        
        if not is_tool_track:
            retained_imported_tracks.append(t)

    script.imported_tracks = retained_imported_tracks
    script.tracks = {}
    script.duration = 0

    script.add_track(TrackType.audio, "Voice Track")
    script.add_track(TrackType.video, "Visual Track")

    # Add Voice Segment
    voice_material_obj = AudioMaterial(voice_path)
    if voice_mat:
        voice_material_obj.material_id = voice_mat.get("id") or voice_mat.get("material_id")
    
    voice_duration_us = int(round(voice_duration * 1e6))
    if hasattr(voice_material_obj, "duration") and voice_material_obj.duration > 0:
        if voice_duration_us > voice_material_obj.duration:
            voice_duration_us = voice_material_obj.duration

    voice_segment = AudioSegment(
        voice_material_obj,
        Timerange(0, voice_duration_us),
        source_timerange=Timerange(0, voice_duration_us)
    )
    script.add_segment(voice_segment, "Voice Track")

    # Add Visual Segments
    synced_segments = 0
    for item in matched_visuals:
        v_path = item["material"].get("path")
        v_start_us = int(round(item["start"] * 1e6))
        v_end_us = int(round(item["end"] * 1e6))
        v_duration_us = v_end_us - v_start_us

        if v_duration_us <= 0:
            continue

        video_material_obj = VideoMaterial(v_path)
        video_material_obj.material_id = item["material"].get("id") or item["material"].get("material_id")

        if item["type"] == "video":
            video_material_obj.material_type = "video"
        else:
            video_material_obj.material_type = "photo"

        source_tr = Timerange(0, v_duration_us)
        target_tr = Timerange(v_start_us, v_duration_us)

        if item["type"] == "video":
            if hasattr(video_material_obj, "duration") and video_material_obj.duration > 0:
                if source_tr.end > video_material_obj.duration:
                    source_tr.duration = video_material_obj.duration

        segment = VideoSegment(
            video_material_obj,
            target_tr,
            source_timerange=source_tr
        )
        script.add_segment(segment, "Visual Track")
        synced_segments += 1

    # Deduplicate materials
    json_str = script.dumps()
    final_data = json.loads(json_str)

    if "materials" in final_data:
        for cat in final_data["materials"]:
            if isinstance(final_data["materials"][cat], list):
                seen = set()
                deduped = []
                for m in final_data["materials"][cat]:
                    m_id = m.get("id") or m.get("material_id")
                    if m_id not in seen:
                        seen.add(m_id)
                        deduped.append(m)
                final_data["materials"][cat] = deduped

    # 8. SAVE
    with open(draft_content_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    dirs_to_clean = list(set([project_dir, active_timeline_dir]))
    for d in dirs_to_clean:
        if not d or not os.path.exists(d):
            continue
        for f_name in os.listdir(d):
            if f_name.endswith(".tmp") or f_name.startswith("template"):
                tmp_file_path = os.path.join(d, f_name)
                try:
                    os.remove(tmp_file_path)
                except Exception:
                    try:
                        shutil.copy2(draft_content_path, tmp_file_path)
                    except Exception:
                        pass

    print(f"Đồng bộ SRT thành công! Project đã được lưu.")
    print(f"Tổng kết: {synced_segments} segments đã đồng bộ, {warnings_count} warnings, chênh lệch điều chỉnh: {adjustment_made:.2f}s.")

if __name__ == "__main__":
    main()
