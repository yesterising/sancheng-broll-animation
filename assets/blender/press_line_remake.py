"""Rebuild the workcell, retaining only the tested original worker and console."""
import bpy
import argparse
import sys
import shutil
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-dir',required=True,type=Path)
parser.add_argument('--events',type=Path,default=Path(__file__).with_name('press_line_events.json'))
parser.add_argument('--width',type=int,default=1280)
parser.add_argument('--height',type=int,default=720)
parser.add_argument('--samples',type=int,default=48)
parser.add_argument('--still',type=int,help='Render one requested layout frame, 1..336')
args=parser.parse_args(argv)
if not bpy.app.background: parser.error('Run in an isolated Blender background process')
if min(args.width,args.height,args.samples)<=0: parser.error('Dimensions and samples must be positive')
if args.still is not None and not 1<=args.still<=336: parser.error('still must be 1..336')
ROOT=args.project_dir.expanduser().resolve()
if ROOT.exists(): parser.error('project-dir already exists; use a new workspace')
E=json.loads(args.events.read_text())
if (E['duration'],E['fps'])!=(14,24): parser.error('This reference is fixed at 14 seconds and 24fps; adapt a task copy for other timing')
if 'SC worker' not in bpy.data.objects: parser.error('Load the seed blend produced by brick_factory.py first')
ROOT.mkdir(parents=True)
(ROOT/'frames').mkdir()
OUT=ROOT
shutil.copyfile(args.events,ROOT/'press_line_events.json')
FPS=E['fps']
END=int(FPS*E['duration'])
scene=bpy.context.scene
bpy.context.preferences.filepaths.save_version=0
scene.frame_set(1)
worker=bpy.data.objects['SC worker']
upper=bpy.data.objects['Right sleeve']
lower=bpy.data.objects['Right forearm']

hand=bpy.data.objects['Right gripping hand']
def control_empty(name):
    obj=bpy.data.objects.new(name,None)
    scene.collection.objects.link(obj)
    return obj
scene.frame_set(1)
A = Vector((.72, 0, 2.64))
B = Vector((.90, -.10, 2.25))
C = Vector((.94, -.03, 1.80))
arm_data = bpy.data.armatures.new('Fixed-length test arm')
rig = bpy.data.objects.new('Fixed-length test arm', arm_data)
scene.collection.objects.link(rig)
rig.parent = worker
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
b1 = arm_data.edit_bones.new('upper')
b1.head, b1.tail = A, B
b2 = arm_data.edit_bones.new('forearm')
b2.head, b2.tail = B, C
b2.parent, b2.use_connect = b1, True
bpy.ops.object.mode_set(mode='OBJECT')
target = control_empty('Wrist IK target')
pole = control_empty('Elbow pole')
pole.parent = worker
pole.location = (1.5, -1.5, 2.3)
ik = rig.pose.bones['forearm'].constraints.new('IK')
ik.target, ik.pole_target, ik.chain_count = target, pole, 2
ik.use_stretch = False
ik.iterations = 128
for bone in rig.pose.bones:
    bone.ik_stretch = 0

# Retain the original mesh appearance, driven by rigid fixed-length bone matrices.
for obj, bone_name, radius in [(upper, 'upper', .22), (lower, 'forearm', .17)]:
    obj.animation_data_clear()
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    length = arm_data.bones[bone_name].length
    obj.data = obj.data.copy()
    obj.data.transform(Matrix.Translation((0, length/2, 0)) @ Matrix.Diagonal((radius, length/2, radius, 1)))
    con = obj.constraints.new('COPY_TRANSFORMS')
    con.target, con.subtarget = rig, bone_name
hand.animation_data_clear()
con = hand.constraints.new('COPY_LOCATION')
con.target, con.subtarget, con.head_tail = rig, 'forearm', 1
contact_local = Vector((0, 0, -.295))


def descendants(obj):
    for child in obj.children:
        yield child
        yield from descendants(child)

console_names=['Control pedestal','Pedestal orange stripe','Control deck','Control screen',
               'Screen bar','Button metallic bezel','START button','Pedestal badge']
keep={worker,rig,target,upper,lower,*descendants(worker)}
keep.update(o for o in bpy.data.objects if any(o.name.startswith(n) for n in console_names))
for obj in list(bpy.data.objects):
    if obj not in keep:
        bpy.data.objects.remove(obj,do_unlink=True)
for obj in keep:
    obj.animation_data_clear()
    obj.hide_render=False
    obj.hide_viewport=False
worker.location=(-4,-1.5,.08)
worker.rotation_euler=(0,0,0)
for obj in keep:
    if obj.name.startswith('Leg pivot'):
        obj.rotation_euler=(0,0,0)
rig.name='SC fixed-length arm rig'
target.name='SC wrist control'
scene.timeline_markers.clear()
scene.frame_start,scene.frame_end=1,END
scene.render.fps=FPS
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x,scene.render.resolution_y=args.width,args.height
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
scene.render.film_transparent=False
scene.render.filepath=str(ROOT/'frames'/'frame_')
scene.eevee.taa_render_samples=args.samples
scene.eevee.use_raytracing=True
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes['Background']
bg.inputs['Color'].default_value=(.13,.17,.22,1)
bg.inputs['Strength'].default_value=.35
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'

def material(name,color,rough=.3,metal=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    p.inputs['Coat Weight'].default_value=.22 if not metal else .05
    return m

navy=bpy.data.materials['Deep petrol ABS']
teal=bpy.data.materials['Ocean teal ABS']
ivory=bpy.data.materials['Warm ivory ABS']
orange=bpy.data.materials['Safety orange ABS']
dark=bpy.data.materials['Rubber and ink']
steel=bpy.data.materials['Satin metal']
floor=material('Slate baseplate',(.095,.16,.19),.43)
backdrop=material('Studio blue-grey',(.026,.041,.062),.62)
graphite=material('Anodized carrier',(.09,.13,.16),.3,.4)
green=material('Running signal',(.06,.7,.19),.25)
amber=material('Ready signal',(.95,.22,.025),.27)
blue=material('Vacuum signal',(.04,.58,.85),.25)
white_led=material('Inspection signal',(.64,.9,.85),.23)

def finish(obj,name,mat,parent=None):
    obj.name=name
    if mat: obj.data.materials.append(mat)
    if parent: obj.parent=parent
    return obj

def box(name,loc,dims,mat,bevel=.04,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=finish(bpy.context.object,name,mat,parent)
    obj.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new('Molded edge','BEVEL')
        mod.width=bevel
        mod.segments=3
        obj.modifiers.new('Corner normals','WEIGHTED_NORMAL')
    return obj

def cyl(name,loc,radius,depth,mat,parent=None,vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc)
    obj=finish(bpy.context.object,name,mat,parent)
    mod=obj.modifiers.new('Rounded lip','BEVEL')
    mod.width=min(.018,depth*.15)
    mod.segments=3
    obj.modifiers.new('Cylindrical normals','WEIGHTED_NORMAL')
    for poly in obj.data.polygons: poly.use_smooth=True
    return obj

def empty(name,loc=(0,0,0)):
    obj=bpy.data.objects.new(name,None)
    scene.collection.objects.link(obj)
    obj.location=loc
    return obj

def brick(name,loc,dims,mat,nx,ny,parent=None):
    obj=box(name,loc,dims,mat,.035,parent)
    for i in range(nx):
        for j in range(ny):
            x=loc[0]+(i-(nx-1)/2)*dims[0]/nx
            y=loc[1]+(j-(ny-1)/2)*dims[1]/ny
            cyl(name+' stud',(x,y,loc[2]+dims[2]/2+.03),min(dims[0]/nx,dims[1]/ny)*.22,.06,mat,parent,24)
    return obj

def text(name,value,loc,size,mat):
    data=bpy.data.curves.new(name,'FONT')
    data.body=value
    data.size=size
    data.align_x='CENTER'
    data.extrude=.001
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(math.pi/2,0,0)
    obj.data.materials.append(mat)
    return obj

def line(name,points,radius,mat):
    data=bpy.data.curves.new(name,'CURVE')
    data.dimensions='3D'
    data.bevel_depth=radius
    data.bevel_resolution=3
    spline=data.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for p,co in zip(spline.bezier_points,points):
        p.co=co
        p.handle_left_type=p.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    data.materials.append(mat)
    return obj

def smooth(a,b,t):
    p=max(0,min(1,(t-a)/(b-a)))
    return p*p*(3-2*p)

def phase(name,t): return smooth(*E[name],t)
def key(obj,f,path='location'): obj.keyframe_insert(data_path=path,frame=f)

# An open miniature workcell: the foreground remains free of structural pillars.
box('Studio ground',(0,0,-.46),(200,200,.15),backdrop,0)
box('Rounded display plinth',(.3,.5,-.22),(13.8,8.4,.4),navy,.18)
box('Studded baseplate',(.3,.5,.015),(13.5,8.1,.08),floor,.1)
for x in range(-8,10):
    for y in [-4,-3,4,5]:
        cyl('Baseplate stud',(x*.68,y*.68,.08),.105,.045,floor,vertices=20)
for x in [-5.5,-3.4,-1.3,.8,2.9,5.0]:
    brick('Low rear wall',(x,4.1,.58),(2.0,.32,1.02),ivory,4,1)
    box('Rear inset',(x,3.925,.64),(1.6,.035,.34),teal,.015)
line('Orange power cable',[(-2.65,-1.2,.13),(-2.65,-.65,.13),(-1.0,-.65,.13),(-.65,.8,.13),(.3,1.3,.13)],.045,orange)

# Synchronized conveyor, with a lower return path so ribs never teleport visibly.
X0,X1=-2.15,5.55
Y=.4
box('Conveyor housing',((X0+X1)/2,Y,.94),(X1-X0+.25,1.42,.34),teal,.10)
box('Belt body',((X0+X1)/2,Y,1.105),(X1-X0,1.12,.065),dark,.025)
for x in [-1.7,.6,3.0,5.1]:
    for y in [-.18,.98]:
        brick('Belt leg',(x,y,.42),(.25,.28,.74),ivory,1,1)
        box('Leg foot',(x,y,.09),(.48,.49,.12),navy)
for y in [-.29,1.09]:
    box('Side rail',((X0+X1)/2,y,1.14),(X1-X0+.05,.11,.18),ivory,.03)
    for x in [-1.8,4.9]:
        box('Safety stripe',(x,y-.065,1.15),(.55,.025,.09),orange,.012)
rollers=[]
for x in [X0,X1]:
    o=cyl('End drive roller',(x,Y,.94),.18,1.15,steel)
    o.rotation_euler.x=math.pi/2
    rollers.append(o)
loop=2*(X1-X0)
rib_count=84
ribs=[box('Closed-loop belt rib %02d'%i,(0,Y,1.15),(.09,1.05,.035),navy,.009) for i in range(rib_count)]

# Base shell: visible alignment pins permit a short, readable press-fit travel.
product=empty('Workpiece base')
box('Orange shell',(0,0,0),(.74,.74,.4),orange,.055,product)
box('Product label',(0,-.378,.015),(.42,.018,.13),ivory,.008,product)
for x in [-.26,.26]:
    for y in [-.26,.26]:
        cyl('Alignment pin',(x,y,.245),.045,.07,orange,product,24)
for y in [-.32,.32]:
    box('Shell rim',(0,y,.225),(.67,.055,.03),orange,.012,product)

def cap(name,loc):
    root=empty(name,loc)
    brick(name+' plate',(0,0,0),(.82,.82,.18),teal,2,2,root)
    return root

fedcap=cap('Top cap picked by vacuum',(1.6,2.7,2.02))
cap('Next cap',(1.6,2.7,1.78))
cap('Bottom cap',(1.6,2.7,1.54))
brick('Feeder pedestal',(1.6,2.7,.68),(1.20,1.20,1.20),ivory,2,2)
box('Feeder platform',(1.6,2.7,1.39),(1.26,1.26,.12),navy,.05)
for x in [1.09,2.11]:
    for y in [2.19,3.21]:
        box('Magazine corner guide',(x,y,1.85),(.095,.095,.78),steel,.018)
text('Feeder label','01 / FEED',(1.6,2.087,.72),.16,navy)

# Cartesian vacuum transfer: rigid side cantilever leaves the press axis open.
for y in [3.25]:
    brick('Transfer rail column',(2.65,y,2.0),(.36,.40,3.9),ivory,1,1)
    box('Column foot',(2.65,y,.13),(.75,.75,.18),navy)
box('Transfer linear beam',(2.65,1.65,4.05),(.38,3.8,.32),orange,.05)
box('Linear polished rail',(2.43,1.65,4.06),(.055,3.64,.11),steel,.015)
carriage=box('Y carriage',(2.45,2.7,3.91),(.51,.46,.4),navy,.06)
box('Vacuum Y badge',(2.45,2.455,3.93),(.23,.018,.12),teal,.012)
arm=empty('Vacuum Z arm')
box('Vacuum cantilever',(2.025,0,.37),(.85,.24,.13),teal,.045,arm)
box('Z sleeve',(2.45,0,.37),(.29,.29,.35),navy,.035,arm)
cyl('Vacuum fitting',(1.6,0,.235),.065,.23,steel,arm)
cyl('Suction cup',(1.6,0,.14),.105,.10,dark,arm)
vacrod=cyl('Telescopic vacuum rod',(2.45,2.7,3.2),.065,1,steel)
vac_led=cyl('Vacuum status',(2.45,2.7,4.15),.075,.07,blue)
line('Vacuum hose',[(2.7,3.6,.25),(2.7,3.65,2.4),(2.7,3.6,4.3),(2.7,1.6,4.3)],.04,dark)

# Open C-frame press: the upright is behind and to the left of the product.
for k in range(7):
    brick('C-frame mast',(.3,1.4,.35+k*.48),(.55,.5,.45),ivory if k%2 else orange,2,1)
brick('Press X bridge',(.95,1.4,3.78),(1.9,.62,.42),orange,4,1)
box('Press Y bridge',(1.6,.87,3.78),(.64,1.12,.42),orange,.06)
box('Cylinder body',(1.6,.4,3.61),(.4,.42,.48),teal,.05)
press_head=empty('Press head')
box('Press shoe',(0,0,.11),(.94,.94,.22),teal,.055,press_head)
box('Contact face',(0,0,.018),(.87,.87,.036),steel,.012,press_head)
press_rod=cyl('Press telescopic piston',(1.6,.4,3),.08,1,steel)
text('Press number','02',(.3,1.132,2.6),.23,navy)

# Output sensor and shallow collection stop, outside the important contact view.
box('Inspection rear post',(4.45,1.38,1.65),(.22,.22,1.1),teal)
box('Inspection light',(4.45,1.25,2.16),(.26,.28,.16),white_led,.035)
box('Finished stop',(5.45,.4,1.35),(.10,1.12,.26),ivory,.025)
box('Output fascia',(4.7,-.365,.93),(1.4,.04,.25),navy,.025)
text('Output label','03 / OUT',(4.7,-.39,.87),.15,ivory)

stack=[]
cyl('Signal stem',(.3,1.4,3.99),.05,.25,steel)
for i,mat in enumerate([green,amber]):
    stack.append(cyl('Signal lamp '+str(i),(.3,1.4,4.18+i*.18),.12,.14,mat))

head=bpy.data.objects['Head pivot']
hand=bpy.data.objects['Right gripping hand']
button=bpy.data.objects['START button']
CONTACT=Vector((0,0,-.295))
REST=Vector((.94,-.03,1.80))

def emission(mat,frame,strength):
    p=mat.node_tree.nodes['Principled BSDF']
    p.inputs['Emission Color'].default_value=mat.diffuse_color
    p.inputs['Emission Strength'].default_value=strength
    p.inputs['Emission Strength'].keyframe_insert('default_value',frame=frame)

for f in range(1,END+1):
    t=(f-1)/FPS
    scene.frame_set(f)
    look=phase('look',t)
    reach=phase('reach',t)*(1-phase('withdraw',t))
    press=phase('button_down',t)*(1-phase('button_up',t))
    button.location.z=2.045-.095*press
    key(button,f)
    hand.rotation_euler=(0,-.45*reach,0)
    key(hand,f,'rotation_euler')
    bpy.context.view_layer.update()
    surface=button.matrix_world@Vector((0,0,.07))
    rotation=worker.matrix_world.to_3x3()@hand.rotation_euler.to_matrix()
    target.location=(worker.matrix_world@REST).lerp(surface-rotation@CONTACT,reach)
    key(target,f)
    head.rotation_euler=(.20*look*(1-smooth(3.1,4.2,t)),0,.95*look-.35*smooth(3.1,4.2,t))
    key(head,f,'rotation_euler')
    travel=2.85*phase('belt_in',t)+3.40*phase('belt_out',t)
    product.location=(-1.25+travel,.4,1.36)
    key(product,f)
    for i,obj in enumerate(ribs):
        p=(i*loop/rib_count+travel)%loop
        obj.location=(X0+p,Y,1.1425) if p<=X1-X0 else (X1-(p-(X1-X0)),Y,.72)
        key(obj,f)
    for obj in rollers:
        obj.rotation_euler.y=travel/.18
        key(obj,f,'rotation_euler')
    cap_z=2.02+.43*phase('grip_lift',t)-.72*phase('grip_place',t)-.04*phase('press_fit',t)
    cap_y=2.7-2.3*phase('grip_transfer',t)
    fedcap.location=(1.6+3.40*phase('belt_out',t),cap_y,cap_z)
    key(fedcap,f)
    grip_z=2.7-.68*phase('grip_down',t)+.43*phase('grip_lift',t)-.72*phase('grip_place',t)+.72*phase('grip_clear',t)
    grip_y=2.7-2.3*phase('grip_transfer',t)+2.3*phase('grip_return',t)
    arm.location=(0,grip_y,grip_z)
    key(arm,f)
    carriage.location.y=grip_y
    key(carriage,f)
    rod_bottom=grip_z+.54
    vacrod.location=(2.45,grip_y,(rod_bottom+3.82)/2)
    vacrod.scale.z=3.82-rod_bottom
    key(vacrod,f)
    key(vacrod,f,'scale')
    vac_led.location.y=grip_y
    key(vac_led,f)
    shoe_bottom=3.15-1.27*phase('press_approach',t)-.04*phase('press_fit',t)+1.31*phase('press_retract',t)
    press_head.location=(1.6,.4,shoe_bottom)
    key(press_head,f)
    piston_bottom=shoe_bottom+.22
    press_rod.location.z=(piston_bottom+3.75)/2
    press_rod.scale.z=3.75-piston_bottom
    key(press_rod,f)
    key(press_rod,f,'scale')
    if f in [1,54,55,END]:
        emission(green,f,0 if f<55 else 2.1)
        emission(amber,f,1.5 if f<55 else 0)
    if f in [1,89,90,164,165,END]:
        emission(blue,f,1.7 if 90<=f<165 else 0)
    if f in [1,293,294,305,306,END]:
        emission(white_led,f,2 if 294<=f<=305 else .3)

def camera(name,start,end,pos0,pos1,target0,target1,lens):
    data=bpy.data.cameras.new(name)
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    data.lens=lens
    data.clip_end=250
    for f,pos,aim in [(start,pos0,target0),(end,pos1,target1)]:
        obj.location=pos
        obj.rotation_euler=(Vector(aim)-obj.location).to_track_quat('-Z','Y').to_euler()
        key(obj,f)
        key(obj,f,'rotation_euler')
    marker=scene.timeline_markers.new(name,frame=start)
    marker.camera=obj
    return obj

c1=camera('01 / WORKCELL',1,29,(10,-16,10),(9.8,-15.7,9.8),(.0,.6,1.6),(.1,.7,1.6),46)
camera('02 / BUTTON',30,72,(-.3,-10.2,6.4),(-.5,-9.9,6.2),(-3.25,-1.5,2.5),(-3.25,-1.5,2.5),49)
camera('03 / VACUUM FEED',73,139,(7.7,-5.3,6.7),(7.2,-5.0,6.4),(1.9,2.0,2.7),(1.8,1.5,2.5),52)
camera('04 / PRESS FIT',140,247,(6.6,-5.7,4.8),(6.2,-5.3,4.6),(1.7,.65,2.4),(1.7,.6,2.2),57)
camera('05 / FINISHED',248,END,(9.8,-12.2,7.6),(9.1,-11.2,6.9),(1.2,.7,1.7),(2.3,.6,1.65),52)
scene.camera=c1

def area(name,loc,power,color,size,aim):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=power
    data.color=color
    data.shape='DISK'
    data.size=size
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(Vector(aim)-obj.location).to_track_quat('-Z','Y').to_euler()

area('Warm key',(-4,-6,10),1800,(1,.86,.70),7,(0,.7,1))
area('Large cool edge',(4,5,9),1900,(.53,.76,1),6,(0,.7,1))
area('Soft frontal fill',(1,-8,5),700,(.78,.88,1),8,(1,.5,1))
area('Amber figure rim',(-7,2,7),800,(1,.55,.30),5,(-4,-1,2))

# Linear baked channels preserve explicit contact intervals between evaluated frames.
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for point in fc.keyframe_points: point.interpolation='LINEAR'

scene.frame_set(1)
metrics={'frames':END,'fps':FPS,'duration':E['duration'],'fixed_arm':{},'contact_max_error':0}
lengths={name:[] for name in ['upper','forearm']}
for f in range(1,END+1):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    evaluated=rig.evaluated_get(depsgraph)
    for name in lengths:
        bone=evaluated.pose.bones[name]
        lengths[name].append((bone.tail-bone.head).length)
    if 49<=f<=62:
        h=hand.evaluated_get(depsgraph)
        b=button.evaluated_get(depsgraph)
        error=((h.matrix_world@CONTACT)-(b.matrix_world@Vector((0,0,.07)))).length
        metrics['contact_max_error']=max(metrics['contact_max_error'],error)
    assert abs(fedcap.scale.x-1)<1e-6
for name,values in lengths.items():
    metrics['fixed_arm'][name]={'min':min(values),'max':max(values)}
assert metrics['contact_max_error']<.01,metrics
assert E['grip_return'][1]<E['press_approach'][0]
assert E['press_retract'][1]<E['belt_out'][0]
(ROOT/'build-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'press_line.blend'))
if args.still is not None:
    scene.frame_set(args.still)
    scene.render.filepath=str(ROOT/('layout_%04d.png'%args.still))
    bpy.ops.render.render(write_still=True)
print('BUILT_REMAKE '+json.dumps(metrics))
