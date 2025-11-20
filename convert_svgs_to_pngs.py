import os
import argparse
import io
import cairosvg
from PIL import Image

def convert_svgs(input_dir, output_dir, target_width=1920, target_height=1080):
    """
    Converts a directory of SVGs to PNGs with fixed resolution, 
    white background, and centered padding.
    """
    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Get list of SVG files and sort them naturally
    # This assumes files are named like 1.svg, 2.svg or standard alphanumeric sorting
    files = [f for f in os.listdir(input_dir) if f.lower().endswith('.svg')]
    
    # Sort files. If filenames are integers (1.svg, 2.svg), sort numerically.
    # Otherwise sort alphabetically.
    try:
        files.sort(key=lambda f: int(os.path.splitext(f)[0]))
    except ValueError:
        files.sort()

    total_files = len(files)
    print(f"Found {total_files} SVG files in '{input_dir}'. Processing...")

    for index, filename in enumerate(files):
        file_path = os.path.join(input_dir, filename)
        
        try:
            # --- Step 1: Determine Aspect Ratio ---
            # We render the SVG to memory at its native/default size first
            # to figure out its aspect ratio.
            byte_data = cairosvg.svg2png(url=file_path)
            original_image = Image.open(io.BytesIO(byte_data))
            orig_w, orig_h = original_image.size
            
            aspect_ratio = orig_w / orig_h
            target_ratio = target_width / target_height

            # --- Step 2: Calculate Render Dimensions ---
            # We want to render the SVG crisp at the target size, not resize a blurry small one.
            # We tell CairoSVG exactly how big to make the actual number part.
            
            render_width = target_width
            render_height = target_height

            if aspect_ratio > target_ratio:
                # Image is wider than target 16:9; fit to width, adjust height
                render_height = int(target_width / aspect_ratio)
            else:
                # Image is taller than target 16:9; fit to height, adjust width
                render_width = int(target_height * aspect_ratio)

            # --- Step 3: Render High-Res SVG ---
            # Render the SVG again, this time forcing the calculated dimensions
            high_res_data = cairosvg.svg2png(
                url=file_path, 
                output_width=render_width, 
                output_height=render_height
            )
            img = Image.open(io.BytesIO(high_res_data)).convert("RGBA")

            # --- Step 4: Create Canvas ---
            # Create white background canvas (1920x1080)
            canvas = Image.new("RGBA", (target_width, target_height), (255, 255, 255, 255))
            
            # Calculate centering position
            x_offset = (target_width - render_width) // 2
            y_offset = (target_height - render_height) // 2

            # Paste the rendered SVG onto the canvas using the alpha channel as mask
            canvas.paste(img, (x_offset, y_offset), img)

            # --- Step 5: Save ---
            # Generate filename: 0001.png, 0002.png, etc.
            output_filename = f"{index + 1:04d}.png"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save as PNG (convert to RGB to remove alpha channel since bg is white now)
            canvas.convert("RGB").save(output_path, "PNG")
            
            print(f"[{index+1}/{total_files}] Saved {output_filename} (derived from {filename})")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print("Processing complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch convert SVGs to 1080p PNGs with padding.")
    
    parser.add_argument("input_dir", help="Path to directory containing SVG files")
    parser.add_argument("output_dir", help="Path to directory to save PNG files")
    parser.add_argument("--width", type=int, default=1920, help="Target width (default: 1920)")
    parser.add_argument("--height", type=int, default=1080, help="Target height (default: 1080)")

    args = parser.parse_args()

    convert_svgs(args.input_dir, args.output_dir, args.width, args.height)
