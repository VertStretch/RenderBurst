bl_info = {
    "name": "Render Burst",
    "category": "Render",
    "author" : "Aidy Burrows, Gleb Alexandrov, Roman Alexandrov, CreativeShrimp.com <support@creativeshrimp.com>",
    "version" : (1, 0, 27),
    "description" :
            "Render all cameras, one by one, and store results.",
}

import os
import bpy

class RenderBurst(bpy.types.Operator):
    """Render all cameras"""
    bl_idname = "render.renderburst"
    bl_label = "Render Burst"

    _timer = None
    shots = None
    stop = None
    rendering = None
    path = "//"
    disablerbbutton = False

    def pre(self, dummy):
        self.rendering = True

    def post(self, dummy):
        self.shots.pop(0) 
        self.rendering = False

    def cancelled(self, dummy):
        self.stop = True

    def execute(self, context):
        self.stop = False
        self.rendering = False
        scene = context.scene
        wm = context.window_manager
        if wm.rb_filter.rb_filter_enum == 'selected':
            self.shots = [ o.name+'' for o in bpy.context.selected_objects if o.type=='CAMERA' and o.is_visible(scene) == True]
        else:
            self.shots = [ o.name+'' for o in bpy.data.objects if o.type=='CAMERA' and o.is_visible(scene) == True ]


        if len(self.shots) < 0:
            self.report({"WARNING"}, 'No cameras defined')
            return {"FINISHED"}        

        bpy.app.handlers.render_pre.append(self.pre)
        bpy.app.handlers.render_post.append(self.post)
        bpy.app.handlers.render_cancel.append(self.cancelled)

        self._timer = context.window_manager.event_timer_add(0.5, context.window)
        context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == 'TIMER':

            if True in (not self.shots, self.stop is True): 

                bpy.app.handlers.render_pre.remove(self.pre)
                bpy.app.handlers.render_post.remove(self.post)
                bpy.app.handlers.render_cancel.remove(self.cancelled)
                context.window_manager.event_timer_remove(self._timer)

                return {"FINISHED"} 

            elif self.rendering is False: 
                                          
                sc = bpy.context.scene
                sc.camera = bpy.data.objects[self.shots[0]] 	

                lpath = self.path

                if sc.render.filepath != '':
                    lpath = os.path.dirname(sc.render.filepath)
                    lpath = lpath.rstrip('/')
                    if lpath=='':
                        lpath='/' 
                    lpath+='/'

                sc.render.filepath = lpath + self.shots[0] + sc.render.file_extension
                bpy.ops.render.render("INVOKE_DEFAULT", write_still=True)

        return {"PASS_THROUGH"}

# ui part
class RbFilterSettings(bpy.types.PropertyGroup):
    rb_filter_enum = bpy.props.EnumProperty(
        name = "Filter",
        description = "Choose your destiny",
        items = [
            ("all", "All Cameras", "Render all cameras"),
            ("selected", "Selected Only", "Render selected only"),
        ],
        default = 'all'
    )   


class RenderBurstCamerasPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Render Burst"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

    def draw(self, context):
        wm = context.window_manager
        box = self.layout.box()
        row = box.row()
        row.prop(wm.rb_filter, "rb_filter_enum", expand=True)
        row = self.layout.row()
        row.operator("rb.renderbutton", text='Render!')
        row = self.layout.row()

class OBJECT_OT_RBButton(bpy.types.Operator):
    bl_idname = "rb.renderbutton"
    bl_label = "Render"

    #@classmethod
    #def poll(cls, context):
    #    return True
 
    def execute(self, context):
        if bpy.context.scene.render.filepath is None or len(bpy.context.scene.render.filepath)<1:
            self.report({"ERROR"}, 'Output path not defined. Please, define the output path on the render settings panel')
            return {"FINISHED"}

        animation_formats = [ 'FFMPEG', 'AVI_JPEG', 'AVI_RAW', 'FRAMESERVER' ]

        if bpy.context.scene.render.image_settings.file_format in animation_formats:
            self.report({"ERROR"}, 'Animation formats are not supported. Yet :)')
            return {"FINISHED"}

        bpy.ops.render.renderburst()
        return{'FINISHED'}

def menu_func(self, context):
    self.layout.operator(RenderBurst.bl_idname)

def register():
    bpy.utils.register_module(__name__)
    bpy.types.WindowManager.rb_filter = bpy.props.PointerProperty(type=RbFilterSettings)
    bpy.types.INFO_MT_render.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_render.remove(menu_func)

if __name__ == "__main__":
    register()