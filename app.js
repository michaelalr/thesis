// Application state
let csvData = [];  // The user's CSV data
let currentIndex = 0;  // Tracks which image we are displaying
let userAnswers = [];  // Collects user's answers
let selectedBbox = null;  // Track the selected bounding box
let imageElement = document.getElementById('image'); // Cache the image element

// Load the CSV data for the user
fetch('csv_files/user_1_images.csv')  // Ensure the correct path to your CSV file
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok: ' + response.statusText);
    }
    return response.text();
  })
  .then(csv => {
    Papa.parse(csv, {
      header: true,
      complete: function(results) {
        csvData = results.data;
        displayImage();
      }
    });
  })
  .catch(error => {
    console.error('Error loading CSV:', error);
  });

// Display the current image
function displayImage() {
  let row = csvData[currentIndex];
  if (!row) return;

  imageElement.src = row.image_path;
  selectedBbox = null; // Reset selected bounding box
  clearPreviousHighlights(); // Clear previous highlights

  // Clear previous bounding boxes and display new ones
  displayBoundingBoxes(JSON.parse(row.containers_bbox));
}

// Display bounding boxes on the image
function displayBoundingBoxes(bboxes) {
  let container = document.getElementById('image-container');

  // Clear previous boxes
  container.querySelectorAll('.bbox').forEach(box => box.remove());

  // Listen for image load event to ensure dimensions are ready
  imageElement.onload = () => {
    const imgWidth = imageElement.naturalWidth; // Get the natural width of the image
    const imgHeight = imageElement.naturalHeight; // Get the natural height of the image

    bboxes.forEach((bbox) => {
      // Calculate positions based on natural image size
      const left = (bbox[0] / imgWidth) * 100;
      const top = (bbox[1] / imgHeight) * 100;
      const width = ((bbox[2] - bbox[0]) / imgWidth) * 100;
      const height = ((bbox[3] - bbox[1]) / imgHeight) * 100;

      let box = document.createElement('div');
      box.className = 'bbox';
      box.style.left = left + '%';
      box.style.top = top + '%';
      box.style.width = width + '%';
      box.style.height = height + '%';

      // Allow only clicking inside bounding boxes
      box.addEventListener('click', (event) => {
        event.stopPropagation(); // Prevent click on image
        selectedBbox = bbox; // Save the selected bounding box
        highlightSelectedBox(box); // Highlight selected box
      });

      container.appendChild(box);
    });
  };

  // Trigger image load to ensure dimensions are calculated
  imageElement.src = row.image_path; // Set image src again to ensure load event fires
}

// Highlight the selected bounding box
function highlightSelectedBox(selectedBox) {
  // Clear previous highlights
  document.querySelectorAll('.bbox').forEach(box => box.classList.remove('highlighted'));
  selectedBox.classList.add('highlighted'); // Highlight the selected box
}

// Clear highlights on buttons and bounding boxes
function clearPreviousHighlights() {
  document.getElementById('no-container').style.backgroundColor = ''; // Reset background
  document.querySelectorAll('.bbox').forEach(box => box.classList.remove('highlighted')); // Clear previous highlights
}

// Prepare for user selection
function prepareUserSelection() {
  document.getElementById('no-container').onclick = () => {
    selectedBbox = []; // If the user chooses "not in any container"
    highlightNoContainerSelection();
  };

  document.getElementById('finish').onclick = () => {
    if (selectedBbox !== null) {
      confirmFinishImage();
    } else {
      alert('Please select a container or choose "Not in Any Container".');
    }
  };
}

// Highlight the "Not in Any Container" selection
function highlightNoContainerSelection() {
  document.getElementById('no-container').style.backgroundColor = 'lightgray'; // Change background to highlight
  clearPreviousHighlights(); // Clear previous bounding box highlights
}

// Confirm if the user finished with the current image
function confirmFinishImage() {
  if (confirm('Are you finished with this image?')) {
    saveUserSelection(selectedBbox);
    currentIndex++; // Move to the next image

    // Check if we have reached the end
    if (currentIndex < csvData.length) {
      displayImage();
    } else {
      alert('You have reached the end of the images! Your answers will be saved.');
      downloadCSV(); // Download answers before exiting
      window.close(); // Optionally close the window after downloading
    }
  }
}

// Save the user's selection (bbox or empty list)
function saveUserSelection(chosenBbox) {
  let row = csvData[currentIndex];
  userAnswers.push({
    image_path: row.image_path,
    room_type: row.room_type,
    chosen_annotation_bbox: chosenBbox
  });
}

// Convert userAnswers to CSV and download
function downloadCSV() {
  let csv = Papa.unparse(userAnswers);
  let blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  let link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'user_1_answers.csv';
  link.click();
}

// Initialize user selection handling
prepareUserSelection();
