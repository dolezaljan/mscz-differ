#!/usr/bin/env python3
import zipfile
import xml.etree.ElementTree as ET
import shutil
import argparse

import sys
import os

bright_pink_dict = {'r':"240", 'g':"0", 'b':"160", 'a':"255"}

duration_type_to_64ths = {
  '64th': 1,
  '32nd': 2,
  '16th': 4,
  'eighth': 8,
  'quarter': 16,
  'half': 32,
  'whole': 64,
}

duration_to_64ths = {
  '1/8':  8,
  '2/8': 16,
  '3/8': 24,
  '4/8': 32,
  '1/4': 16,
  '2/4': 32,
  '3/4': 48,
  '4/4': 64,
  '1/8': 8,
  '2/8': 16,
  '3/8': 24,
  '4/8': 32,
  '5/8': 40,
  '6/8': 48,
  '7/8': 56,
  '8/8': 64,
}

# chord or rest
def elem_64s_duration(elem):
    durationType = elem.find('durationType').text
    if durationType == 'measure':
      dur = duration_to_64ths[elem.find('duration').text]
    else:
      dur = duration_type_to_64ths[elem.find('durationType').text]
      dots = elem.find('dots')
      if dots is not None:
          if dots.text == '1':
              dur += dur/2
          if dots.text == '2':
              dur += 3*dur/4
    return int(dur)

duration_types = ['64th', '32nd', '16th', 'eighth', 'quarter', 'half', 'whole']

def parse_mscz(filepath):
    """Parses an mscz file and returns the root XML element."""
    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        mscxs = [n for n in zip_ref.namelist() if n.endswith('.mscx')]
        if len(mscxs) > 1:
            print(f"Warning: {filepath} contains multiple mscx files {mscxs}, taking the first", file=sys.stderr)
        with zip_ref.open(mscxs[0]) as xml_file:
            tree = ET.parse(xml_file)
            return tree.getroot()

def has_note(root, staff_idx, measure_idx, voice_idx, beat_in_measure_64th, tone_duration_64th, pitch):
    staffs = root.findall('.//Score/Staff')
    if staff_idx >= len(staffs):
        return False
    s = staffs[staff_idx]
    measures = s.findall('Measure')
    if measure_idx >= len(measures):
        return False
    m = measures[measure_idx]
    voices = m.findall('voice')
    if voice_idx >= len(voices):
        return False
    v = voices[voice_idx]
    current_64th = 0
    for element in v.findall('*'):
        if element.tag in ['Rest', 'Chord']:
            el_duration = elem_64s_duration(element)
            current_64th += el_duration
            if element.tag == 'Chord' and beat_in_measure_64th == current_64th:
                if el_duration != tone_duration_64th:
                    return False
                chord_pitches = [n.find('pitch').text for n in element.findall('Note')]
                if pitch not in chord_pitches:
                    return False
                return True

def mark_differences(root_a, root_b):
    for staff_idx, staff in enumerate(root_a.findall('.//Score/Staff')):
        for measure_idx, measure in enumerate(staff.findall('Measure')):
            for voice_idx, voice in enumerate(measure.findall('voice')):
                current_64th = 0
                for element in voice.findall('*'):
                    if element.tag in ['Rest', 'Chord']:
                        el_duration = elem_64s_duration(element)
                        current_64th += el_duration
                        if element.tag == 'Chord':
                            for note in element.findall('Note'):
                                note_pitch = note.find('pitch').text
                                if not has_note(root_b, staff_idx, measure_idx, voice_idx, current_64th, el_duration, note_pitch):
                                    color = ET.SubElement(note, 'color')
                                    color.attrib.update(bright_pink_dict)

def save_diff(root, output_path, original_mscz_path):
    """Saves the modified XML to a new mscz file."""
    with zipfile.ZipFile(original_mscz_path, 'r') as zip_read:
        mscx = [n for n in zip_read.namelist() if n.endswith('.mscx')][0]
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_write:
            for item in zip_read.infolist():
                if item.filename != mscx:
                    zip_write.writestr(item, zip_read.read(item.filename))
            xml_string = ET.tostring(root, encoding='utf-8', xml_declaration=True).decode()
            zip_write.writestr(mscx, xml_string)

def create_diff(file_a, file_b):
    root_a = parse_mscz(file_a)
    root_b = parse_mscz(file_b)

    base_name_a, _ = os.path.splitext(os.path.basename(file_a))
    base_name_b, _ = os.path.splitext(os.path.basename(file_b))

    mark_differences(root_a, root_b)
    mark_differences(root_b, root_a)
    save_diff(root_a, f'{base_name_a}-{base_name_b}.mscz', file_a)
    save_diff(root_b, f'{base_name_b}-{base_name_a}.mscz', file_b)

def main():
    parser = argparse.ArgumentParser(description="Generate a diff between two MuseScore files.")
    parser.add_argument("file_a", help="Path to the first MuseScore file (mscz).")
    parser.add_argument("file_b", help="Path to the second MuseScore file (mscz).")

    args = parser.parse_args()

    try:
        create_diff(args.file_a, args.file_b)
        print(f"Diffs created successfully!")
    except FileNotFoundError:
        print("Error: One or both input files not found.")
    except zipfile.BadZipFile:
        print("Error: One or both input files are not valid mscz files.")

if __name__ == "__main__":
    main()
