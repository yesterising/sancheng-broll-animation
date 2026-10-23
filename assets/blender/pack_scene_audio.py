"""Keep the same standalone mechanical sound track inside the delivered blend."""
import bpy
import argparse
import sys
from pathlib import Path

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sound',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args(argv)
if not bpy.app.background: parser.error('Run with Blender --background')
if not args.sound.is_file(): parser.error('Sound file is missing')
output=args.output.expanduser().resolve()
if output.exists(): parser.error('Output already exists; choose a new filename')
output.parent.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
bpy.context.preferences.filepaths.save_version=0
editor=scene.sequence_editor_create()
strips=editor.strips
for strip in list(strips):
    strips.remove(strip)
for sound in list(bpy.data.sounds):
    bpy.data.sounds.remove(sound)
strip=strips.new_sound('Original mechanical Foley',str(args.sound.resolve()),channel=1,frame_start=1)
scene.render.use_sequencer=False
scene.sync_mode='AUDIO_SYNC'
scene.frame_set(1)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(output))
print('SOUND_PACKED',strip.sound.name, bool(strip.sound.packed_file))
