import matplotlib.pyplot as plt
from matplotlib.table import Table
from PIL import Image

# Open the existing PNG file
existing_image = Image.open('BC_102F.png')

# Resize the image to a smaller size while maintaining its aspect ratio
new_size = (300, 450)  # Set the desired size
existing_image = existing_image.resize(new_size)

# Create a Matplotlib figure and axis based on the resized image size
fig, ax = plt.subplots(figsize=new_size)

# Display the resized image
ax.imshow(existing_image)

# Define the data for the 2x2 table
data = [['Cell 1', 'Cell 2'],
        ['Cell 3', 'Cell 4']]

# Create a table and add it to the axis
table = ax.table(cellText=data, loc='center', cellLoc='center', colWidths=[0.2, 0.2])
table.auto_set_font_size(False)
table.set_fontsize(14)
table.scale(1, 1)

# Hide the axes
ax.axis('off')

# Save the modified image with the table as a new PNG file
plt.savefig('modified_image.png', bbox_inches='tight', pad_inches=0.1)

# Show the modified image (optional)
plt.show()