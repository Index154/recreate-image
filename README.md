# Recreate Image
A custom script for Stable Diffusion WebUI for recreating images with the same or slightly modified parameters. It works by automatically using the parameters found in an image's metadata. Supports batch processing from a folder.

Disclaimer: The script can obviously only work with images that still have their original generation metadata. If this information is missing or false then you will not get the same results. Additional extensions and features like ControlNet, FABRIC, ADetailer and such are also hard to replicate and may cause minor or major inconsistencies.

## Installation & usage
1. In the WebUI navigate to: Extensions -> Install from URL
2. Paste this link into the "URL for extension's git repository" box: https://github.com/Index154/recreate-image
3. Click on Install and wait for it to finish installing
4. Select the "Installed" tab and click on "Apply and restart UI"
5. To use it select it in the Scripts dropdown of the txt2img or img2img tab, configure the settings, then upload an image or activate batch mode and enter an input folder path. When you start a generation it will run

# Functionality summary
- Allows uploading / dragging a single image into the UI
- Also supports batch input from a folder
- You can select which parameters of the original image should be kept the same from the following options:
  - Positive prompt
  - Negative prompt
  - Seed
  - Sampler settings (includes sampling method, CFG scale and sampling steps)
- Every other parameter will be taken from your actual UI settings
- You can make it so the script throws an error and aborts in the following cases which may otherwise make recreation impossible:
  - The image's original model is not the same as your currently selected one
  - The image was generated with [ControlNet](https://github.com/Mikubill/sd-webui-controlnet)
  - The image was generated with [FABRIC](https://github.com/dvruette/sd-webui-fabric)
- With batch input enabled you can also make it so the script's errors don't stop the whole process but instead simply skip over any images causing them
- You can also make the script automatically use the input image as a ControlNet input. This can be useful when recreating the image proves difficult with just the other parameters
- Alternatively you can make ControlNet only be applied when the script would otherwise throw an error (see above for configurable error behavior). For example only if the original image was also generated using ControlNet or FABRIC
- If the script enables ControlNet it will try to use the same values as were used for the original image for the following settings: Weight, pixel perfect, guidance start, guidance end, preprocessor and model (I know using the same preprocessor setting is kinda stupid, I might change this later). The setting for guidance start and guidance end will default to 0 and 1 if not found in the image metadata. All other values will be taken from your UI settings (might make this more flexible later)
- With batch input you can also choose to only process a limited number of randomly selected images from the folder. If enabled the script will use your batch count setting to determine the number of images to process
- This has support for the same string substitution synatx for positive prompts as my other custom script [Random ControlNet Input](https://github.com/Index154/Random-ControlNet-Input). Check the README of that for more details if you care
