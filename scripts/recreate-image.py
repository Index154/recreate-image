import os

from PIL import Image, ImageOps, UnidentifiedImageError
import gradio as gr
import random
import copy
from io import BytesIO
import base64

import importlib
import modules.scripts as scripts
import modules.shared as shared
import modules.images as images
from modules import script_callbacks
from modules import images as imgutil
from modules.processing import process_images, Processed
from modules.shared import opts, state

class Script(scripts.Script):

    def title(self):
        return "Recreate image"

    def ui(self, is_img2img):
        uiImageInput = gr.Image(label="Image", source="upload", interactive=True, type="pil")
        uiSamePosPrompt = gr.Checkbox(True, label="Use original positive prompt")
        uiSameNegPrompt = gr.Checkbox(True, label="Use original negative prompt")
        uiSameSeed = gr.Checkbox(True, label="Use original seed")
        uiSameSampling = gr.Checkbox(True, label="Use original sampler settings")
        uiControlNetAssist = gr.Checkbox(False, label="Always use the input image as the ControlNet input to assist with recreation")
        uiConditionalControlNetAssist = gr.Checkbox(False, label="If an error would be raised, instead use the input image as the ControlNet input")
        uiModelErr = gr.Checkbox(True, label="Raise error if a different model was used")
        uiControlNetErr = gr.Checkbox(True, label="Raise error if a ControlNet was used")
        uiFabricErr = gr.Checkbox(True, label="Raise error if Fabric was used")
        uiEnableBatch = gr.Checkbox(False, label="Batch from folder")
        uiBatchPath = gr.Textbox(label="Batch input folder path", lines=1)
        uiSkipBatchErr = gr.Checkbox(True, label="Skip images in batch mode when errors occur")
        uiRandom = gr.Checkbox(False, label="Pick images randomly from folder (one per batch count)")
        return [uiImageInput, uiBatchPath, uiSamePosPrompt, uiSameNegPrompt, uiSameSeed, uiRandom, uiEnableBatch, uiSameSampling, uiModelErr, uiControlNetErr, uiFabricErr, uiSkipBatchErr, uiControlNetAssist, uiConditionalControlNetAssist]

    def run(self, p, uiImageInput, uiBatchPath, uiSamePosPrompt, uiSameNegPrompt, uiSameSeed, uiRandom, uiEnableBatch, uiSameSampling, uiModelErr, uiControlNetErr, uiFabricErr, uiSkipBatchErr, uiControlNetAssist, uiConditionalControlNetAssist):
    
        # Callback before an image is saved - Change filename to the same as the original input image
        targetFileName = ''
        def on_before_image_saved(params):
            if targetFileName != '' : params.filename = '\\'.join(params.filename.split('\\')[:-1]) + '\\' + targetFileName
            return params
    
        script_callbacks.on_before_image_saved(on_before_image_saved)
    
        # Abort if there are no active selections
        if(not uiSamePosPrompt and not uiSameNegPrompt and not uiSameSeed):
            return
        
        if(uiImageInput is None and (not uiEnableBatch or uiBatchPath == '')):
            raise Exception('Missing input image or batch path in custom script')
            return
        
        for k, v in p.override_settings.items():
            print(str(k) + ' = ' + str(v))
        
        # Function for replacing text in string
        def replaceText(text):
            for replace in replaces:
                if(replace is not None):
                    parts = replace[1:-1].split('=>')
                    text = text.replace(parts[0], '=>'.join(parts[1:]))
            return text
        
        # Function for generating an image (or batch) with the same parameters as an input image
        def recreateImg(img, p):
            p2 = copy.copy(p)
            condControlNetAssist = False
            p2.init_images = [img] * p2.batch_size
            
            # Get image info - genInfo contains all of it within one string
            genInfo, items = imgutil.read_info_from_image(img)
            genInfo = genInfo.split('\n')
            details = genInfo[2].split(', ')
            checkpointName = p2.sd_model.sd_model_checkpoint.split('.')[0].split('\\')[-1]
            
            # Change prompt information to that of the input image if enabled
            if uiSamePosPrompt : p2.prompt = genInfo[0]
            if uiSameNegPrompt : p2.negative_prompt = genInfo[1][17:]
            if uiSameSeed : p2.seed = int(details[3][6:])
            if uiSameSampling:
                p2.cfg_scale = int(details[2][11:])
                p2.sampler_name = details[1][9:]
                p2.steps = int(details[0][7:])
                
            if(uiModelErr and details[5][7:] != checkpointName):
                if uiConditionalControlNetAssist : condControlNetAssist = True
                if (uiEnableBatch and uiSkipBatchErr) and not uiConditionalControlNetAssist : return None
                if not uiConditionalControlNetAssist : raise Exception('The original model for this image is: ' + details[5][7:])
                
            if(uiControlNetErr and ', ControlNet' in genInfo[2]):
                if uiConditionalControlNetAssist : condControlNetAssist = True
                if (uiEnableBatch and uiSkipBatchErr) and not uiConditionalControlNetAssist : return None
                if not uiConditionalControlNetAssist : raise Exception('The original image was generated with the assistance of ControlNet')
                
            if(uiFabricErr and ', fabric_start:' in genInfo[2]):
                if uiConditionalControlNetAssist : condControlNetAssist = True
                if (uiEnableBatch and uiSkipBatchErr) and not uiConditionalControlNetAssist : return None
                if not uiConditionalControlNetAssist : raise Exception('The original image was generated with the assistance of FABRIC')
            
            # Hook ControlNet if enabled
            if uiControlNetAssist or condControlNetAssist:
                controlNetModule = importlib.import_module('extensions.sd-webui-controlnet.scripts.external_code', 'external_code')
                controlNetList = controlNetModule.get_all_units_in_processing(p2)
                io = BytesIO()
                img.save(io, format='PNG')
                imgData = controlNetModule.to_base64_nparray(base64.b64encode(io.getvalue()).decode())
                
                # Try to get values from original prompt, otherwise keep current values aside from guidance start & end
                weight = controlNetList[0].weight
                pixel_perfect = controlNetList[0].pixel_perfect
                guidance_start = 0.0
                guidance_end = 1.0
                module = controlNetList[0].module
                model = controlNetList[0].model
                if ', ControlNet' in genInfo[2]:
                    controlNetDetails = genInfo[2].split(', ControlNet')[1]
                    weight = float(controlNetDetails.split(', Weight: ')[1].split(',')[0])
                    if controlNetDetails.split(', Pixel Perfect: ')[1].split(',')[0] == 'True' : pixel_perfect = True
                    else : pixel_perfect = False
                    guidance_start = float(controlNetDetails.split(', Guidance Start: ')[1].split(',')[0])
                    guidance_end = float(controlNetDetails.split(', Guidance End: ')[1].split(',')[0])
                    module = controlNetDetails.split('Module: ')[1].split(',')[0]
                    model = controlNetDetails.split(', Model: ')[1].split(',')[0]
                
                controlNetList[0].image = imgData
                controlNetList[0].enabled = True
                controlNetList[0].weight = weight
                controlNetList[0].pixel_perfect = pixel_perfect
                controlNetList[0].guidance_start = guidance_start
                controlNetList[0].guidance_end = guidance_end
                controlNetList[0].module = module
                controlNetList[0].model = model
                controlNetModule.update_cn_script_in_processing(p2, controlNetList)
            
            # Modify with replacement strings
            p2.prompt = replaceText(p2.prompt)
            
            proc = process_images(p2)
            return proc
        
        # Get substitution strings from prompt and remove them
        import re
        pattern = r'!.*?=>.*?!'
        replaces = re.findall(pattern, p.prompt)
        p.prompt = re.sub(pattern, '', p.prompt)
        # Remove other syntax
        pattern = r'!.*?=.*?!'
        p.prompt = re.sub(pattern, '', p.prompt)
        
        # Batch process from folder
        batch_results = None
        if(uiEnableBatch and uiBatchPath != ''):
            
            images = list(shared.walk_files(uiBatchPath, allowed_extensions=(".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")))
            
            # Select x random images instead of all if enabled (rebuild image array)
            newImages = []
            if(uiRandom):
                # n_iter is the batch count
                for i in range(p.n_iter):
                    roll = random.randrange(0, len(images))
                    newImages.append(images[roll])
                p.n_iter = 1
                images = newImages
            
            print(f"Will process {len(images)} images, creating {p.n_iter * p.batch_size} for each.")
            state.job_count = len(images) * p.n_iter
            
            # Loop through images
            for i, image in enumerate(images):
                state.job = f"{i+1} out of {len(images)}"
                targetFileName = image.split('\\')[-1]
                
                if state.skipped:
                    state.skipped = False

                if state.interrupted or state.stopping_generation:
                    break

                try:
                    img = Image.open(image)
                except UnidentifiedImageError as e:
                    print(e)
                    continue
                # Use the EXIF orientation of photos taken by smartphones
                img = ImageOps.exif_transpose(img)
                
                # Process one image
                proc = recreateImg(img, p)
                
                # Add result to results
                if proc is not None:
                    if batch_results:
                        batch_results.images.extend(proc.images)
                        batch_results.infotexts.extend(proc.infotexts)
                    else:
                        batch_results = proc
                
            return batch_results
                
        else:
            proc = recreateImg(uiImageInput, p)
            return proc
