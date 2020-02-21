bl_info = {
    "name": "Render Burst",
    "category": "Render",
    "blender": (2, 80, 0),
    "author" : "Aidy Burrows, Gleb Alexandrov, Roman Alexandrov, CreativeShrimp.com <support@creativeshrimp.com>, Christian Brinkmann (p2or)",
    "version" : (1, 1, 30),
    "description" : "Render all cameras, one by one, and store results.",
    "location": "Render Properties > Render Burst",
    "support": "COMMUNITY",
}

import bpy
import os


# -------------------------------------------------------------------
#    Operators
# -------------------------------------------------------------------

class RB_OT_RenderInit(bpy.types.Operator):
    bl_idname = "rb.render"
    bl_label = "Render Burst"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        rd = context.scene.render
        
        if rd.filepath is None or len(rd.filepath) < 1:
            self.report({"ERROR"}, 'Output path not defined. Please, define the output path on the render settings panel')
            return {"FINISHED"}

        if rd.is_movie_format: 
            self.report({"ERROR"}, 'Animation formats are not supported. Yet :)')
            return {"FINISHED"}

        bpy.ops.rb.renderburst()
        return{'FINISHED'}


class RB_OT_RenderAllCameras(bpy.types.Operator):
    """Modal Render Operator, allows to render within the UI"""
    bl_idname = "rb.renderburst"
    bl_label = "Render Burst"

    _timer = shots = stop = rendering = None

    def filter_cameras(self, context):
        c = context
        rb = c.window_manager.rb_settings
        usr_objs = c.selected_objects if rb.rb_filter == 'SEL' else c.visible_objects
        return [o.name for o in usr_objs if o.type == 'CAMERA' and o.visible_get()]

    def pre(self, dummy, thrd=None):
        self.rendering = True

    def post(self, dummy, thrd=None):
        self.shots.pop(0) 
        self.rendering = False

    def cancelled(self, dummy, thrd=None):
        self.stop = True

    def execute(self, context):
        scene = context.scene
        self.shots = self.filter_cameras(context)
        self.stop = False
        self.rendering = False
        
        if len(self.shots) < 0:
            self.report({"WARNING"}, 'No cameras defined')
            return {"FINISHED"}        

        bpy.app.handlers.render_pre.append(self.pre)
        bpy.app.handlers.render_post.append(self.post)
        bpy.app.handlers.render_cancel.append(self.cancelled)

        self._timer = bpy.context.window_manager.event_timer_add(0.3, window=context.window)
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

                lpath = "//"
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
                    if lpath == "":
                        lpath = "/" 
                    lpath += "/"

                sc.render.filepath = lpath + self.shots[0] + sc.render.file_extension
                bpy.ops.render.render("INVOKE_DEFAULT", write_still=True)

        return {"PASS_THROUGH"}


# -------------------------------------------------------------------
#    UI
# -------------------------------------------------------------------

class RB_SettingsClass(bpy.types.PropertyGroup):
    rb_filter: bpy.props.EnumProperty(
        name = "Filter",
        description = "Choose your destiny",
        items = [
            ("ALL", "All Cameras", "Render all cameras"),
            ("SEL", "Selected Only", "Render selected only"),
        ], default = 'ALL'
    )   


class RB_PT_RenderPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Render Burst"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        rb = context.window_manager.rb_settings
        layout = self.layout
        row = layout.row()
        row.prop(rb, "rb_filter", expand=True)
        row = self.layout.row()
        row.operator(RB_OT_RenderInit.bl_idname, text='Render!')
        row = self.layout.row()


def draw_render_burst(self, context):
    self.layout.operator(RB_OT_RenderInit.bl_idname, icon='CAMERA_DATA')


# -------------------------------------------------------------------
#    Registration
# -------------------------------------------------------------------

classes = (
    RB_SettingsClass,
    RB_OT_RenderInit,
    RB_OT_RenderAllCameras,
    RB_PT_RenderPanel
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    bpy.types.WindowManager.rb_settings = bpy.props.PointerProperty(type=RB_SettingsClass)
    bpy.types.TOPBAR_MT_render.append(draw_render_burst)


def unregister():
    bpy.types.TOPBAR_MT_render.remove(draw_render_burst)
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.WindowManager.rb_settings

if __name__ == "__main__":
    register()
