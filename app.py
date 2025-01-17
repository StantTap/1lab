from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use 'Agg' backend for matplotlib
import matplotlib.pyplot as plt
import uuid

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def adjust_color_intensity(image, adjust_channels):
    """
    Adjust the intensity of specified color channels.
    adjust_channels: dict with keys 'R', 'G', 'B' and adjustment factors as values.
    """
    img_array = np.array(image)
    for channel, factor in adjust_channels.items():
        if channel == 'R':
            img_array[:, :, 0] = np.clip(img_array[:, :, 0] * factor, 0, 255)
        elif channel == 'G':
            img_array[:, :, 1] = np.clip(img_array[:, :, 1] * factor, 0, 255)
        elif channel == 'B':
            img_array[:, :, 2] = np.clip(img_array[:, :, 2] * factor, 0, 255)
    adjusted_image = Image.fromarray(img_array.astype('uint8'), 'RGB')
    return adjusted_image

def plot_color_distribution(image, filename):
    """Plot and save the color distribution histogram of the image."""
    img_array = np.array(image)
    plt.figure()
    colors = ('r', 'g', 'b')
    channel_ids = (0, 1, 2)
    for channel_id, color in zip(channel_ids, colors):
        histogram, bin_edges = np.histogram(
            img_array[:, :, channel_id], bins=256, range=(0, 255)
        )
        plt.plot(bin_edges[0:-1], histogram, color=color)
    plt.title('Color Distribution')
    plt.xlabel('Color value')
    plt.ylabel('Pixels')
    plot_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    plt.savefig(plot_path)
    plt.close()
    return plot_path

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'image' not in request.files:
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Save the uploaded file
            filename = secure_filename(file.filename)
            basename, ext = os.path.splitext(filename)
            unique_id = uuid.uuid4().hex
            original_filename = f"{basename}_{unique_id}{ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            file.save(file_path)

            # Get adjustment factors from the form
            adjust_factors = {}
            for color in ['R', 'G', 'B']:
                factor = request.form.get(f'adjust_{color}', type=float)
                if factor is not None and factor != 1.0:
                    adjust_factors[color] = factor

            # Open the image
            image = Image.open(file_path)
            # Plot original color distribution
            original_hist_name = f"hist_original_{unique_id}.png"
            original_hist_path = plot_color_distribution(image, original_hist_name)
            original_image_url = url_for('static', filename=f'uploads/{original_filename}')
            original_hist_url = url_for('static', filename=f'processed/{original_hist_name}')

            # Adjust image
            adjusted_image = adjust_color_intensity(image, adjust_factors)
            adjusted_filename = f"{basename}_adjusted_{unique_id}{ext}"
            adjusted_file_path = os.path.join(app.config['PROCESSED_FOLDER'], adjusted_filename)
            adjusted_image.save(adjusted_file_path)

            # Plot adjusted color distribution
            adjusted_hist_name = f"hist_adjusted_{unique_id}.png"
            adjusted_hist_path = plot_color_distribution(adjusted_image, adjusted_hist_name)
            adjusted_image_url = url_for('static', filename=f'processed/{adjusted_filename}')
            adjusted_hist_url = url_for('static', filename=f'processed/{adjusted_hist_name}')

            return render_template('result.html',
                                   original_image_url=original_image_url,
                                   adjusted_image_url=adjusted_image_url,
                                   original_hist_url=original_hist_url,
                                   adjusted_hist_url=adjusted_hist_url)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)