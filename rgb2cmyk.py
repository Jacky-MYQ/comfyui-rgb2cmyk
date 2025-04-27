from PIL import Image, ImageCms
import folder_paths
import os
import numpy as np
class RGB2CMYK:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def get_icc_paths(cls):
        # 获取icc目录
        icc_set = {'.icc'}
        icc_paths = []
        for path in os.listdir(os.path.join(os.path.dirname(__file__), "color_profiles")):
            if os.path.splitext(path)[1].lower() in icc_set:
                icc_paths.append(path)
        return sorted(icc_paths)
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required":{
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."}),
                "rgb_icc_profile_name": (s.get_icc_paths(), {"default":"AppleRGB.icc","tooltip": "The name of the RGB profile."}),
                "cmyk_icc_profile_name": (s.get_icc_paths(), {"default":"CoatedFOGRA39.icc","tooltip": "The name of the CMYK profile."}),
                }
        }

    RETURN_TYPES = ()
    FUNCTION = "convert"
    CATEGORY = "RGB2CMYK"
    OUTPUT_NODE = True


    def convert(self, images, rgb_icc_profile_name, cmyk_icc_profile_name, filename_prefix="ComfyUI"):
        if rgb_icc_profile_name == cmyk_icc_profile_name:
            raise ValueError("RGB and CMYK ICC profiles must be different.")
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()

        #颜色文件
        rgb_profile = os.path.join(os.path.dirname(__file__), "color_profiles", rgb_icc_profile_name)
        cmyk_profile = os.path.join(os.path.dirname(__file__), "color_profiles", cmyk_icc_profile_name)

        # 使用相对色度渲染意图
        renderingIntent = ImageCms.Intent.RELATIVE_COLORIMETRIC  

        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            img = img.convert('RGB')

            # 使用色彩管理系统进行转换
            # 直接使用 img.convert('CMYK') 是简单矩阵转换，会丢失信息
            # 如果输入和输出配置文件相同，转换映射无法正确生成，因为没有颜色空间之间的差异需要映射。
            if os.path.exists(rgb_profile) and os.path.exists(cmyk_profile):
                transform = ImageCms.buildTransform(
                    rgb_profile,
                    cmyk_profile,
                    "RGB",
                    "CMYK",
                    renderingIntent=renderingIntent
                )
                img = ImageCms.applyTransform(img, transform)
            else:
                img = img.convert('CMYK')  # 回退到简单转换
                print("警告：未找到ICC配置文件，使用基本CMYK转换")
                print(rgb_profile)
                print(os.path.dirname(__file__))


            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.tif"
            img.save(os.path.join(full_output_folder, file), 
                        format='TIFF', 
                        compression="tiff_lzw",  # 这是TIFF压缩参数，
                        icc_profile=ImageCms.getOpenProfile(cmyk_profile).tobytes())

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return { "ui": { "images": results } }