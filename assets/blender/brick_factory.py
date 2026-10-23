"""Nine-second, 24 fps reference scene; copy to a task workspace and adapt."""
import argparse
import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-dir', required=True, type=Path, help='New workspace directory; existing directory is refused')
parser.add_argument('--width', type=int, default=1280)
parser.add_argument('--height', type=int, default=720)
parser.add_argument('--samples', type=int, default=32)
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--render', action='store_true', help='Render all 216 frames after saving the scene')
mode.add_argument('--still', type=int, metavar='FRAME', help='Render one requested frame, from 1 through 216')
args = parser.parse_args(argv)
if min(args.width, args.height, args.samples) <= 0:
    parser.error('width, height and samples must be positive')
if args.still is not None and not 1 <= args.still <= 216:
    parser.error('still must be a frame from 1 through 216')
if not bpy.app.background:
    parser.error('run with Blender --background --factory-startup to isolate the scene')
ROOT = args.project_dir.expanduser().resolve()
if ROOT.exists():
    parser.error('project-dir already exists; choose a new directory or render the saved .blend')
ROOT.mkdir(parents=True)
(ROOT / 'frames').mkdir()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = args.width
scene.render.resolution_y = args.height
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start, scene.frame_end = 1, 216
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.filepath = str(ROOT / 'frames' / 'frame_')
scene.render.image_settings.color_mode = 'RGB'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
if hasattr(scene.eevee, 'taa_render_samples'):
    scene.eevee.taa_render_samples = args.samples
if hasattr(scene.eevee, 'use_raytracing'):
    scene.eevee.use_raytracing = True
scene.world.color = (0.12, 0.12, 0.12)
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.085, .13, .19, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4

def mat(name, color, rough=.28, metal=0, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Coat Weight'].default_value = .28
    p.inputs['Coat Roughness'].default_value = .2
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m

navy = mat('Deep petrol ABS', (.025, .105, .145))
teal = mat('Ocean teal ABS', (.025, .41, .43))
white = mat('Warm ivory ABS', (.8, .84, .78))
orange = mat('Safety orange ABS', (1, .21, .035))
yellow = mat('Minifigure yellow ABS', (1, .62, .035))
dark = mat('Rubber and ink', (.012, .022, .026), .48)
steel = mat('Satin metal', (.24, .33, .37), .25, .65)
floor_mat = mat('Dark blue baseplate', (.055, .13, .18), .4)
ground_mat = mat('Studio backdrop', (.012, .028, .045), .6)
cyan = mat('Cyan indicators', (.03, .8, 1), .22, emission=3)
green = mat('Run light', (.12, 1, .25), .2, emission=2.5)
red = mat('Standby amber', (1, .17, .015), .25, emission=1)
screen = mat('Display glass', (.008, .035, .045), .18)

def finish(o, name, material, parent=None):
    o.name = name
    if material:
        o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o

def box(name, loc, dims, material, bevel=.055, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = finish(bpy.context.object, name, material, parent)
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        m = o.modifiers.new('Soft molded edges', 'BEVEL')
        m.width = bevel
        m.segments = 3
        n = o.modifiers.new('Weighted molded normals', 'WEIGHTED_NORMAL')
    return o

def cyl(name, loc, radius, depth, material, parent=None, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = finish(bpy.context.object, name, material, parent)
    b = o.modifiers.new('Cylinder edge', 'BEVEL')
    b.width = min(.035, depth * .12)
    b.segments = 2
    o.modifiers.new('Cylinder normals', 'WEIGHTED_NORMAL')
    for p in o.data.polygons:
        p.use_smooth = True
    return o

def sphere(name, loc, scale, material, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=loc)
    o = finish(bpy.context.object, name, material, parent)
    o.scale = scale
    for p in o.data.polygons:
        p.use_smooth = True
    return o

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    return o

def text(name, value, loc, size, material, rotation=(math.pi/2, 0, 0), parent=None):
    d = bpy.data.curves.new(name, 'FONT')
    d.body, d.size, d.extrude, d.bevel_depth = value, size, .0015, .0008
    d.align_x = 'CENTER'
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location, o.rotation_euler = loc, rotation
    finish(o, name, material, parent)
    return o

studmesh = None
def stud(name, loc, material, parent=None, radius=.14):
    global studmesh
    if studmesh is None:
        temp = cyl('Stud master', (0, 0, -99), 1, .28, None, vertices=24)
        for mod in list(temp.modifiers):
            temp.modifiers.remove(mod)
        studmesh = temp.data
        bpy.data.objects.remove(temp, do_unlink=True)
    mesh = studmesh.copy()
    mesh.materials.append(material)
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.scale = (radius, radius, radius)
    if parent:
        o.parent = parent
    return o

def brick(name, loc, dims, material, nx, ny, parent=None):
    o = box(name, loc, dims, material, .045, parent)
    x, y, z = loc
    for i in range(nx):
        for j in range(ny):
            stud(name + ' stud', (x+(i-(nx-1)/2)*dims[0]/nx, y+(j-(ny-1)/2)*dims[1]/ny, z+dims[2]/2+.035), material, parent, min(dims[0]/nx,dims[1]/ny)*.23)
    return o

def path_curve(name, points, radius, material, parent=None):
    d = bpy.data.curves.new(name, 'CURVE')
    d.dimensions = '3D'
    d.resolution_u = 16
    d.bevel_depth, d.bevel_resolution = radius, 3
    s = d.splines.new('POLY')
    s.points.add(len(points)-1)
    for p, co in zip(s.points, points):
        p.co = (*co, 1)
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    finish(o, name, material, parent)
    return o

def orient_segment(o, a, b, radius):
    a,b = Vector(a),Vector(b)
    delta = b-a
    o.location = (a+b)/2
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = delta.to_track_quat('Z','Y')
    o.scale = (radius, radius, delta.length/2)

def limb(name, material, parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1)
    o = finish(bpy.context.object, name, material, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    return o

# Modular miniature set.
box('Studio floor', (0,0,-.62), (200,200,.2), ground_mat)
box('Display plinth', (0,.7,-.30), (16,10,.5), navy, .2)
box('Baseplate', (0,.7,-.025), (15.7,9.7,.12), floor_mat, .1)
for x in range(-10,11):
    for y in range(-5,7):
        stud('Floor stud', (x*.7,y*.7,.075), floor_mat, radius=.13)
for x in [-6.5,-3.5,-.5,2.5,5.5]:
    brick('Rear wall module', (x,4.6,1.15), (2.9,.45,2.2), white, 6,1)
    box('Teal recessed wall panel', (x,4.34,1.5), (2.55,.08,.85), teal, .02)
    box('Wall cap', (x,4.6,2.36), (2.9,.6,.14), navy)
text('Factory wall branding','SC / MICRO FACTORY',(1.9,4.27,1.4),.3,white)
for x in [-6.5,-3.5,-.5,2.5,5.5]:
    brick('Wall rib', (x-1.35,4.23,1.2), (.16,.18,2.2), orange, 1,1)
path_curve('Power conduit',[(-2.7,-1.2,.2),(-2.7,-.5,.2),(-1,-.5,.2),(-1,.3,.2)],.06,orange)

# Conveyor bed, rollers, safety rails and feet.
for x in [-1.7,.8,3.3,5.6]:
    for y in [.45,2.1]:
        brick('Conveyor foot',(x,y,.4),(.36,.45,.75),white,1,1)
        box('Foot pad',(x,y,.08),(.55,.65,.12),dark)
box('Conveyor housing',(1.9,1.3,1.02),(8.5,2.1,.5),teal,.13)
box('Dark moving bed',(1.9,1.3,1.315),(8.05,1.65,.16),dark,.045)
for x in [-2.08,5.89]:
    roll = cyl('End roller',(x,1.3,1.28),.28,1.7,steel)
    roll.rotation_euler.x = math.pi/2
for y in [.2,2.4]:
    box('Conveyor side rail',(1.9,y,1.29),(8.5,.13,.23),white,.04)
    for x in [-1.6,.7,3.3,5.5]:
        bolt = cyl('Rail bolt',(x,y-.077,1.3),.055,.025,steel,vertices=16)
        bolt.rotation_euler.x = math.pi/2
slats=[]
for i in range(42):
    slats.append(box('Belt rib %02d'%i,(-2.0+i*.19,1.3,1.435),(.10,1.62,.035),navy,.01))
for x in [-2.0,-1.2,4.7,5.5]:
    brick('Safety orange marker',(x,.2,1.44),(.46,.19,.12),orange,1,1)

# The assembly portal is built from visible stacked bricks.
for y in [.12,2.48]:
    for k in range(4):
        brick('Assembly portal block',(1.35,y,1.4+k*.46),(.85,.52,.43),white if k%2 else orange,2,1)
brick('Assembly portal lintel',(1.35,1.3,3.42),(1.05,3.02,.52),orange,2,6)
box('Assembly front fascia',(1.35,-.168,2.95),(.88,.07,.42),navy)
text('Station label','01',(1.35,-.212,2.83),.31,white)
pressroot=empty('Press moving carriage',(1.35,1.3,0))
cyl('Press piston',(0,0,2.7),.115,.9,steel,pressroot)
box('Press head',(0,0,2.2),(.65,.9,.25),teal,.08,pressroot)
box('Press contact plate',(0,0,2.04),(.55,.8,.06),steel,.015,pressroot)
box('Portal light strip',(1.35,.34,3.13),(.54,.08,.07),cyan,.02)
for y in [.55,2.05]:
    box('Machine accent',(.8,y,3.55),(.08,.22,.16),navy,.02)

# Tower lamps and an inspection scanner.
box('Inspection gate',(4.0,2.35,2.0),(.35,.35,1.6),teal)
box('Scanner overhang',(4.0,1.6,2.75),(.38,1.8,.25),white)
box('Scanner cyan lens',(4.0,.7,2.6),(.25,.08,.14),cyan,.025)
lamps=[]
for k in range(3):
    lamps.append(cyl('Stack lamp '+str(k),(2.0,2.5,3.7+k*.19),.13,.14,dark))
cyl('Stack lamp stem',(2.0,2.5,3.47),.065,.35,steel)

# Control pedestal and a physical spring button.
brick('Control pedestal',(-2.65,-1.7,.83),(.83,.82,1.6),white,2,2)
box('Pedestal orange stripe',(-2.65,-2.122,.9),(.62,.035,.14),orange,.015)
box('Control deck',(-2.65,-1.7,1.77),(1.12,1.13,.3),navy,.10)
box('Control screen',(-2.65,-1.43,1.939),(.6,.27,.035),screen,.025)
for i in range(4):
    box('Screen bar',(-2.89+i*.15,-1.43,1.963),(.065,.12,.015),cyan,.006)
cyl('Button metallic bezel',(-2.65,-1.92,1.96),.235,.1,steel)
button=cyl('START button',(-2.65,-1.92,2.045),.19,.14,green)
text('Pedestal badge','SC',(-2.65,-2.125,1.2),.21,teal)

# Original minifigure-style worker: molded head, printed face, workwear, rigid limbs.
worker=empty('SC worker')
box('Hip block',(0,0,1.48),(1.05,.65,.30),navy,.08,worker)
verts=[]
for z,w in [(1.62,.56),(2.78,.68)]:
    verts.extend([(-w,-.34,z),(w,-.34,z),(w,.34,z),(-w,.34,z)])
mesh=bpy.data.meshes.new('Molded trapezoid torso mesh')
mesh.from_pydata(verts,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
torso=bpy.data.objects.new('Molded work jacket',mesh)
bpy.context.collection.objects.link(torso)
finish(torso,torso.name,teal,worker)
b=torso.modifiers.new('Mold seam bevel','BEVEL');b.width=.07;b.segments=4
torso.modifiers.new('Weighted torso normals','WEIGHTED_NORMAL')
for x in [-.38,.38]:
    box('Reflective overall strap',(x,-.354,2.26),(.095,.028,.93),orange,.012,worker)
    box('Strap buckle',(x,-.38,2.56),(.15,.05,.10),steel,.016,worker)
box('Jacket zipper',(0,-.36,2.28),(.025,.025,.83),navy,.003,worker)
box('Pocket',(.19,-.38,2.16),(.22,.06,.21),navy,.02,worker)
text('Workwear mark','SC',(-.16,-.389,2.31),.13,white,parent=worker)
cyl('Neck connector',(0,0,2.89),.23,.24,yellow,worker)
head=empty('Head pivot',(0,0,3.32),worker)
cyl('Yellow molded head',(0,0,0),.46,.78,yellow,head)
for x in [-.16,.16]:
    sphere('Printed black eye',(x,-.44,.07),(.052,.022,.067),dark,head)
    sphere('Eye glint',(x-.013,-.463,.092),(.011,.008,.014),white,head)
smile=[]
for i in range(17):
    x=-.19+i*.38/16
    smile.append((x,-.455,-.10-.09*(1-(x/.19)**2)))
path_curve('Printed smile',smile,.022,dark,head)
cyl('Hardhat brim',(0,0,.43),.55,.085,orange,head)
sphere('Hardhat dome',(0,.025,.47),(.49,.46,.27),orange,head)
box('Hardhat central rib',(0,-.01,.70),(.12,.70,.06),orange,.035,head)
legs=[]
for x in [-.29,.29]:
    leg=empty('Leg pivot',(x,0,1.43),worker)
    box('Rigid trouser leg',(0,0,-.55),(.48,.57,1.0),navy,.055,leg)
    box('Molded boot',(0,-.14,-1.25),(.52,.84,.4),dark,.06,leg)
    box('Knee plate',(0,-.30,-.52),(.32,.06,.25),teal,.025,leg)
    legs.append(leg)
upper=limb('Right sleeve',teal,worker)
lower=limb('Right forearm',teal,worker)
hand=empty('Right gripping hand',parent=worker)
cyl('Hand wrist',(0,0,.02),.115,.24,yellow,hand)
handpoints=[]
for i in range(23):
    a=math.radians(30+i*300/22)
    handpoints.append((.14*math.cos(a),0,.14*math.sin(a)-.09))
path_curve('C-shaped yellow grip',handpoints,.065,yellow,hand)
leftupper=limb('Left sleeve',teal,worker)
leftlower=limb('Left forearm',teal,worker)
leftglove=sphere('Left yellow hand',(-.86,-.03,1.68),(.16,.18,.19),yellow,worker)

# Products start orange, receive a teal top at the assembly station.
products=[]
for i in range(5):
    root=empty('Workpiece %d'%i)
    brick('Orange workpiece',(0,0,0),(.67,.68,.40),orange,2,2,root)
    lid=empty('Finished cap',parent=root)
    brick('Finished teal top',(0,0,.31),(.73,.74,.17),teal,2,2,lid)
    box('Product ivory label',(0,-.353,.03),(.32,.03,.12),white,.01,root)
    products.append((root,lid))

def smooth(a,b,x):
    p=max(0,min(1,(x-a)/(b-a)))
    return p*p*(3-2*p)

def key(o,frame,props=('location',)):
    for p in props:
        o.keyframe_insert(data_path=p,frame=frame)

# Bake movement, rather than relying on frame-change handlers in the .blend.
for f in range(1,217):
    t=(f-1)/24
    approach=smooth(0,1.5,t)
    walk=math.sin(t*10)*(.38 if t<1.4 else .38*(1-smooth(1.4,1.6,t)))
    worker.location=(-5.0+approach, -1.5, abs(walk)*.055)
    worker.rotation_euler=(0,.03*math.sin(t*10)*(1-approach),-.06*smooth(1.4,2.0,t))
    key(worker,f,('location','rotation_euler'))
    for j,leg in enumerate(legs):
        leg.rotation_euler.x=walk*(1 if j==0 else -1)
        key(leg,f,('rotation_euler',))
    reach=smooth(1.55,2.65,t)*(1-smooth(3.1,3.9,t))
    press=smooth(2.65,2.83,t)*(1-smooth(2.98,3.15,t))
    rest=Vector((.94,-.03,1.8))
    target=Vector((-2.65-worker.location.x,-1.92-worker.location.y,2.27-press*.10))
    wrist=rest.lerp(target,reach)
    elbow=Vector((.9,-.10,2.25)).lerp(Vector((1.03,-.17,2.49)),reach)
    orient_segment(upper,(.72,0,2.64),elbow,.22)
    orient_segment(lower,elbow,wrist,.17)
    for o in [upper,lower]:key(o,f,('location','rotation_quaternion','scale'))
    hand.location=wrist
    hand.rotation_euler=(0,-.45*reach,0)
    key(hand,f,('location','rotation_euler'))
    leftw=(-.88,-.02+walk*.35,1.73)
    orient_segment(leftupper,(-.72,0,2.64),(-.93,.04,2.23),.22)
    orient_segment(leftlower,(-.93,.04,2.23),leftw,.17)
    leftglove.location=leftw
    for o in [leftupper,leftlower]:key(o,f,('location','rotation_quaternion','scale'))
    key(leftglove,f)
    head.rotation_euler.z=-.24*reach+.1*smooth(4.1,5,t)
    head.rotation_euler.x=.09*reach
    key(head,f,('rotation_euler',))
    button.location.z=2.045-press*.095
    key(button,f)
    travel=max(0,t-2.9)*1.25
    for i,o in enumerate(slats):
        o.location.x=-2.05+((i*.19+travel)%7.98)
        key(o,f)
    for i,(root,lid) in enumerate(products):
        x=-1.6-i*1.95+travel
        root.location=(x,1.3,1.69)
        root.scale=(1,1,1) if -2.1<x<6 else (.0001,.0001,.0001)
        key(root,f,('location','scale'))
        done=smooth(.65,1.05,x)
        lid.scale=(max(.0001,done),)*3
        lid.location.z=(1-done)*.8
        key(lid,f,('location','scale'))
    # The press follows each passing workpiece.
    active=[max(0,1-abs((-1.6-i*1.95+travel)-1.35)/.44) for i in range(5)]
    pressroot.location.z=.38-.29*max(active) if t>3 else .38
    key(pressroot,f)
    for k,o in enumerate(lamps):
        o.scale=(1,1,1)
        # Per-object light shells retain their physical material, then emission turns on.

for k,o in enumerate(lamps):
    o.data.materials.clear()
    m=mat('Tower active material '+str(k),(.06,.3,.11) if k==0 else (.05,.12,.14),.22)
    o.data.materials.append(m)
    p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Emission Color'].default_value=(.1,1,.24,1) if k==0 else (.02,.7,1,1)
    for f,v in [(1,0),(69+k*5,0),(73+k*5,3.5),(216,3.5)]:
        p.inputs['Emission Strength'].default_value=v
        p.inputs['Emission Strength'].keyframe_insert('default_value',frame=f)

# Distinct camera coverage, with restrained dollies inside each shot.
def camera(name,frames):
    d=bpy.data.cameras.new(name)
    o=bpy.data.objects.new(name,d)
    bpy.context.collection.objects.link(o)
    d.lens=48
    d.clip_end=300
    for f,pos,target,lens in frames:
        o.location=pos
        o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
        d.lens=lens
        key(o,f,('location','rotation_euler'))
        d.keyframe_insert('lens',frame=f)
    marker=scene.timeline_markers.new(name,frame=frames[0][0]);marker.camera=o
    return o

cam1=camera('01 Establish',[(1,(11,-17,12),(0,.8,1.4),48),(46,(10.4,-16.3,11.3),(0,.8,1.4),48)])
camera('02 Button closeup',[(47,(-.3,-9.3,6.2),(-3.35,-1.55,2.63),53),(88,(-.7,-8.9,5.9),(-3.30,-1.55,2.63),53)])
camera('03 Assembly action',[(89,(5.8,-6.5,5.7),(1.25,1.2,2),49),(145,(6.5,-6,5.1),(1.9,1.2,1.9),49)])
camera('04 Running factory',[(146,(10,-15,10.0),(.4,1,1.4),46),(216,(9.4,-14.4,9.2),(.4,1,1.45),46)])
scene.camera=cam1

def area(name,loc,power,color,size,target):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Warm softbox',(-4,-6,11),1850,(1,.82,.63),7,(0,1,0))
area('Cool edge',(5,5,10),2350,(.38,.72,1),6,(0,1,1))
area('Front fill',(1,-10,5),950,(.7,.86,1),8,(0,1,1.5))
area('Left rim',(-8,3,7),1400,(1,.38,.13),5,(-3,0,1))

# Interpolation is linear for baked motion; camera paths remain gently continuous.
for o in bpy.data.objects:
    if o.animation_data and o.animation_data.action:
        action=o.animation_data.action
        try:
            for fc in action.fcurves:
                for kp in fc.keyframe_points:kp.interpolation='LINEAR'
        except AttributeError:
            pass
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'brick_factory.blend'))
print('SCENE_READY', len(bpy.data.objects), 'objects', str(ROOT), flush=True)
if args.still is not None:
    scene.frame_set(args.still)
    scene.render.filepath = str(ROOT / ('keyframe_%04d.png' % args.still))
    bpy.ops.render.render(write_still=True)
elif args.render:
    bpy.ops.render.render(animation=True)
