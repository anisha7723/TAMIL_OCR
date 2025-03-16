function uploadImage() {
    let fileInput = document.getElementById("imageUpload");
    if (fileInput.files.length === 0) {
        alert("Please upload an image.");
        return;
    }
    
    // Simulating text extraction
    document.getElementById("extractionSection").style.display = "block";
    document.getElementById("extractedText").value = "Extracted Tamil text will be displayed here...";
}

function askCorrection() {
    document.getElementById("correctionOptions").style.display = "block";
}

function sentenceCorrection() {
    let textArea = document.getElementById("extractedText");
    textArea.value = "[Sentence corrected] " + textArea.value;
}

function wordCorrection() {
    let textArea = document.getElementById("extractedText");
    textArea.value = "[Word corrected] " + textArea.value;
}

function exportText() {
    let text = document.getElementById("extractedText").value;
    let blob = new Blob([text], { type: "text/plain" });
    let a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "extracted_text.txt";
    a.click();
}