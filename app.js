// Application state
let csvData = [];  // The user's CSV data
let currentIndex = 0;  // Tracks which image we are displaying
let userAnswers = [];  // Collects user's answers

// Load the CSV data for the user
fetch('user1.csv')  // Replace 'user1.csv' with dynamic user-specific CSV paths
  .then(response => response.text())
  .then(csv => {
    Papa.parse(csv, {
      header: true,
      complete: function(results) {
        csvData = results.data;
        displayImage();
      }
    });
  });

// Display the current image and random item
function displayImage() {
  let row = csvData[currentIndex];
  if (!row) return;

  let imageElement = document.getElementById('image');
  imageElement.src = row.image_path;

  // Display a random item from the common_items list
  let commonItems = JSON.parse(row.common_items);
  let randomItem = commonItems[Math.floor(Math.random() * commonItems.length)];
  document.getElementById('random-item').querySelector('span').textContent = randomItem;

  // Display the bounding boxes (containers_bbox) on the image
  displayBoundingBoxes(JSON.parse(row.containers_bbox));

  // Prepare for the user's selection
  prepareUserSelection(row, randomItem);
}

// Display bounding boxes on the image
function displayBoundingBoxes(bboxes) {
  let container = document.getElementById('image-container');

  // Clear previous boxes
  container.querySelectorAll('.bbox').forEach(box => box.remove());

  bboxes.forEach((bbox, index) => {
    let box = document.createElement('div');
    box.className = 'bbox';
    box.style.left = bbox[0] + 'px';
    box.style.top = bbox[1] + 'px';
    box.style.width = (bbox[2] - bbox[0]) + 'px';
    box.style.height = (bbox[3] - bbox[1]) + 'px';
    box.dataset.index = index;

    box.addEventListener('click', () => {
      saveUserSelection(bbox);
    });

    container.appendChild(box);
  });
}

// Prepare for user selection (either bbox or "Not in Any Container")
function prepareUserSelection(row, randomItem) {
  document.getElementById('no-container').onclick = () => {
    saveUserSelection([]);
  };
}

// Save the user's selection (bbox or empty list) and proceed to the next image
function saveUserSelection(chosenBbox) {
  let row = csvData[currentIndex];
  let randomItem = document.getElementById('random-item').querySelector('span').textContent;

  userAnswers.push({
    image_path: row.image_path,
    room_type: row.room_type,
    random_item: randomItem,
    chosen_annotation_bbox: chosenBbox
  });

  // Move to the next image
  currentIndex++;
  if (currentIndex < csvData.length) {
    displayImage();
  } else {
    downloadCSV();
  }
}

// Convert userAnswers to CSV and download
function downloadCSV() {
  let csv = Papa.unparse(userAnswers);
  let blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  let link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'user_answers.csv';
  link.click();
}

// Move to the next image when "Next" is clicked
document.getElementById('next').addEventListener('click', () => {
  currentIndex++;
  if (currentIndex < csvData.length) {
    displayImage();
  } else {
    alert('All images processed!');
    downloadCSV();
  }
});
