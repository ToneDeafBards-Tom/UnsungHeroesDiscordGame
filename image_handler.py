from PIL import Image

async def create_combined_image(self, image_paths):
    images = [Image.open(path) for path in image_paths]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    combined_image_path = "path/to/combined_image.png"  # Update this path
    new_im.save(combined_image_path)
    return combined_image_path