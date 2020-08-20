bl_info = {
    "name": "Render Burst",
    "category": "Render",
    "blender": (2, 80, 0),
    "author" : "Aidy Burrows, Gleb Alexandrov, Roman Alexandrov, CreativeShrimp.com <support@creativeshrimp.com>",
    "version" : (1, 1, 29),
    "description" :
            "Render all cameras, one by one, and store results.",
}

import bpy
import os

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


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

    def pre(self, dummy, thrd = None):
        self.rendering = True

    def post(self, dummy, thrd = None):
        self.shots.pop(0) 
        self.rendering = False

    def cancelled(self, dummy, thrd = None):
        self.stop = True

    def execute(self, context):
        self.stop = False
        self.rendering = False
        scene = bpy.context.scene
        wm = bpy.context.window_manager
        if wm.rb_filter.rb_filter_enum == 'selected':
            self.shots = [ o.name+'' for o in bpy.context.selected_objects if o.type=='CAMERA' and o.visible_get() == True]
        else:
            self.shots = [ o.name+'' for o in bpy.context.visible_objects if o.type=='CAMERA' and o.visible_get() == True ]


        if len(self.shots) < 0:
            self.report({"WARNING"}, 'No cameras defined')
            return {"FINISHED"}        

        bpy.app.handlers.render_pre.append(self.pre)
        bpy.app.handlers.render_post.append(self.post)
        bpy.app.handlers.render_cancel.append(self.cancelled)

        self._timer = bpy.context.window_manager.event_timer_add(0.5, window=bpy.context.window)
        bpy.context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == 'TIMER':

            if True in (not self.shots, self.stop is True): 
                bpy.app.handlers.render_pre.remove(self.pre)
                bpy.app.handlers.render_post.remove(self.post)
                bpy.app.handlers.render_cancel.remove(self.cancelled)
                bpy.context.window_manager.event_timer_remove(self._timer)

                return {"FINISHED"} 

            elif self.rendering is False: 
                                          
                sc = bpy.context.scene
                sc.camera = bpy.data.objects[self.shots[0]] 	

                lpath = self.path
                fpath = sc.render.filepath
                is_relative_path = True

                if fpath != "":
                    if fpath[0]+fpath[1] == "//":
                        is_relative_path = True
                        fpath = bpy.path.abspath(fpath)
                    else:
                        is_relative_path = False

                    lpath = os.path.dirname(fpath)

                    if is_relative_path:
                        lpath = bpy.path.relpath(lpath)

                    lpath = lpath.rstrip("/")
                    lpath = lpath.rstrip("\\")
                    if lpath=="":
                        lpath="/" 
                    lpath+="/"

                sc.render.filepath = lpath + self.shots[0] + sc.render.file_extension
                bpy.ops.render.render("INVOKE_DEFAULT", write_still=True)

        return {"PASS_THROUGH"}

# ui part
class RbFilterSettings(bpy.types.PropertyGroup):
    rb_filter_enum : bpy.props.EnumProperty(
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
        row = self.layout.row()
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
    from bpy.utils import register_class
    register_class(RenderBurst)
    register_class(RbFilterSettings)
    register_class(RenderBurstCamerasPanel)
    register_class(OBJECT_OT_RBButton)
    bpy.types.WindowManager.rb_filter = bpy.props.PointerProperty(type=RbFilterSettings)
    bpy.types.TOPBAR_MT_render.append(menu_func)

def unregister():
    from bpy.utils import unregister_class
    unregister_class(RenderBurst)
    bpy.types.TOPBAR_MT_render.remove(menu_func)
    unregister_class(RbFilterSettings)
    unregister_class(RenderBurstCamerasPanel)
    unregister_class(OBJECT_OT_RBButton)

if __name__ == "__main__":
    register()
