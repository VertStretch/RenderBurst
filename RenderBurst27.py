bl_info = {
    "name": "Render Burst",
    "category": "Render",
    "author": "Aidy Burrows, Gleb Alexandrov, Roman Alexandrov, CreativeShrimp.com <support@creativeshrimp.com>",
    "version": (1, 0, 27),
    "description": "Render all cameras, one by one, and store results.",
}

import os
import bpy
import time
import datetime

from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
    PointerProperty,
)

from bpy.types import Panel, Operator, PropertyGroup

# ------------------------------------------------------------------------
#    HELPERS
# ------------------------------------------------------------------------
def store_orig_render_samples(self, context):
    self.orig_samples = context.scene.cycles.samples


def set_render_samples(samples):
    bpy.context.scene.cycles.samples = samples


def return_cur_cam(self):
    return bpy.data.objects[self.shots[0]]


def return_cam_samples(cam):
    try:
        cam_opts = cam.cam_settings
        samples = cam_opts.rb_samples_int
    except:
        return -1

    return samples


def return_is_cam_selected(cam):
    try:
        cam_opts = cam.cam_settings
        selected = cam_opts.rb_sel_bool
    except:
        return True  # default to true if no setting

    return selected


def return_selected_cams():
    sel_cams = []
    for cam in bpy.data.objects:
        if cam.type == "CAMERA":
            if return_is_cam_selected(cam):
                sel_cams.append(cam)

    return sel_cams


# ------------------------------------------------------------------------
#    RENDER BURST
# ------------------------------------------------------------------------
class RenderBurst(bpy.types.Operator):
    """Render all cameras"""

    bl_idname = "render.renderburst"
    bl_label = "Render Burst"

    _timer = None
    shots = None
    stop = None
    rendering = None
    orig_samples = None
    path = "//"
    disablerbbutton = False

    def pre(self, dummy):
        # Set next cam sample settings if setting exists
        samples = return_cam_samples(return_cur_cam(self))
        if samples > 0:
            set_render_samples(samples)

        self.rendering = True

    def post(self, dummy):
        self.shots.pop(0)
        self.rendering = False

    def cancelled(self, dummy):
        # reset to original sample settings
        set_render_samples(self.orig_samples)
        self.stop = True

    def execute(self, context):
        self.stop = False
        self.rendering = False

        # store original sample settings
        store_orig_render_samples(self, context)

        # get all selected cameras
        self.shots = [cam.name + "" for cam in return_selected_cams()]

        if len(self.shots) < 0:
            self.report({"WARNING"}, "No cameras defined")
            return {"FINISHED"}

        bpy.app.handlers.render_pre.append(self.pre)
        bpy.app.handlers.render_post.append(self.post)
        bpy.app.handlers.render_cancel.append(self.cancelled)

        self._timer = context.window_manager.event_timer_add(0.5, context.window)
        context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        wm = context.window_manager

        if event.type == "TIMER":

            if True in (not self.shots, self.stop is True):

                bpy.app.handlers.render_pre.remove(self.pre)
                bpy.app.handlers.render_post.remove(self.post)
                bpy.app.handlers.render_cancel.remove(self.cancelled)
                context.window_manager.event_timer_remove(self._timer)
                set_render_samples(self.orig_samples)

                return {"FINISHED"}

            elif self.rendering is False:

                sc = bpy.context.scene
                sc.camera = bpy.data.objects[self.shots[0]]

                dt = ""
                lpath = self.path
                #add a datetime stamp to file name if overwrite is not set
                if not wm.rb_filter.rb_overwrite_bool:
                    ts = time.time()
                    dt = "_" + datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H_%M')

                if sc.render.filepath != "":
                    lpath = os.path.dirname(sc.render.filepath)
                    lpath = lpath.rstrip("/")
                    if lpath == "":
                        lpath = "/"
                    lpath += "/"

                sc.render.filepath = lpath + self.shots[0] + dt + sc.render.file_extension
                bpy.ops.render.render("INVOKE_DEFAULT", write_still=True)

        return {"PASS_THROUGH"}


# ui part
class RbFilterSettings(bpy.types.PropertyGroup):
    rb_filter_enum = bpy.props.EnumProperty(
        name="Filter",
        description="Choose your destiny",
        items=[
            ("all", "All Cameras", "Render all cameras"),
            ("selected", "Selected Only", "Render selected only"),
        ],
        default="all",
    )

    rb_overwrite_bool = BoolProperty(
        name="", description="Should output files be overwritten", default=True
    )


class RBCamSettings(PropertyGroup):

    rb_sel_bool = BoolProperty(
        name="", description="Should camera be rendered", default=True
    )

    # will use current render samples setting as default
    rb_samples_int = IntProperty(
        name="Samples",
        description="Render samples for this camera",
        default=128
    )


# ------------------------------------------------------------------------
#    PANEL
# ------------------------------------------------------------------------
class RenderBurstCamerasPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""

    bl_label = "Render Burst"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"

    def draw(self, context):
        wm = context.window_manager
        box = self.layout.box()
        row = box.row()
        row.label(text="Camera Settings:", icon="INFO")

        # cameras
        for cam in bpy.data.objects:
            if cam.type == "CAMERA":
                cam_opts = cam.cam_settings
                row = box.row()
                row.prop(cam, "name", text="Camera")
                row.prop(cam_opts, "rb_samples_int")
                row.prop(cam_opts, "rb_sel_bool")

        
        row = self.layout.row()
        row.prop(wm.rb_filter, "rb_overwrite_bool", text="Overwrite")
        row.operator("rb.renderbutton", text="Render!")
        row = self.layout.row()


class OBJECT_OT_RBButton(bpy.types.Operator):
    bl_idname = "rb.renderbutton"
    bl_label = "Render"

    def execute(self, context):
        if (
            bpy.context.scene.render.filepath is None
            or len(bpy.context.scene.render.filepath) < 1
        ):
            self.report(
                {"ERROR"},
                "Output path not defined. Please, define the output path on the render settings panel",
            )
            return {"FINISHED"}

        animation_formats = ["FFMPEG", "AVI_JPEG", "AVI_RAW", "FRAMESERVER"]

        if bpy.context.scene.render.image_settings.file_format in animation_formats:
            self.report({"ERROR"}, "Animation formats are not supported. Yet :)")
            return {"FINISHED"}

        bpy.ops.render.renderburst()
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(RenderBurst.bl_idname)


def register():
    bpy.utils.register_module(__name__)
    bpy.types.WindowManager.rb_filter = bpy.props.PointerProperty(type=RbFilterSettings)
    bpy.types.Object.cam_settings = PointerProperty(type=RBCamSettings)
    bpy.types.INFO_MT_render.append(menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_render.remove(menu_func)
    del bpy.types.Object.cam_settings


if __name__ == "__main__":
    register()
