document.addEventListener("DOMContentLoaded", () => {
  const imageUpload = document.getElementById("imageUpload");
  const imagePreview = document.getElementById("imagePreview");
  const labeledImageSelect = document.getElementById("labeledImageSelect");
  const fileUploadText = document.getElementById("fileUploadText");

  const btnVehicleIn = document.getElementById("btnVehicleIn");
  const btnVehicleOut = document.getElementById("btnVehicleOut");
  const btnRefreshData = document.getElementById("btnRefreshData");

  const statusMessageDiv = document.getElementById("statusMessage");
  const groqResultDiv = document.getElementById("groqResult");
  const accuracyResultDiv = document.getElementById("accuracyResult");

  const groqPlatSpan = document.getElementById("groqPlat");
  const groqTypeSpan = document.getElementById("groqType");

  const truePlatSpan = document.getElementById("truePlat");
  const trueTypeSpan = document.getElementById("trueType");
  const plateAccuracySpan = document.getElementById("plateAccuracy");
  const typeAccuracySpan = document.getElementById("typeAccuracy");
  const overallAccuracySpan = document.getElementById("overallAccuracy");
  const accuracyMessageSpan = document.getElementById("accuracyMessage");
  const inferenceTimeSpan = document.getElementById("inferenceTime"); // <--- Get the new span

  const currentParkingTableBody = document.querySelector(
    "#currentParkingTable tbody"
  );
  const parkingHistoryTableBody = document.querySelector(
    "#parkingHistoryTable tbody"
  );

  let selectedFile = null;

  async function loadLabeledImages() {
    try {
      const response = await fetch("/labeled_images");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      data.images.forEach((imgPath) => {
        const option = document.createElement("option");
        option.value = imgPath;
        option.textContent = imgPath.split("/").pop();
        labeledImageSelect.appendChild(option);
      });
    } catch (error) {
      console.error("Error loading labeled images:", error);
      setStatusMessage("Gagal memuat daftar gambar berlabel.", "error");
    }
  }

  labeledImageSelect.addEventListener("change", () => {
    if (labeledImageSelect.value !== "none") {
      imagePreview.src = `/${labeledImageSelect.value}`;
      imagePreview.style.display = "block";
      selectedFile = null;
      imageUpload.value = "";
      fileUploadText.textContent =
        "Pilih File Gambar Baru... (Gambar terlabel dipilih)";
    } else {
      imagePreview.style.display = "none";
      imagePreview.src = "#";
      fileUploadText.textContent = "Pilih File Gambar Baru...";
    }
  });

  imageUpload.addEventListener("change", (event) => {
    selectedFile = event.target.files[0];
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        imagePreview.src = e.target.result;
        imagePreview.style.display = "block";
      };
      reader.readAsDataURL(selectedFile);
      labeledImageSelect.value = "none";
      fileUploadText.textContent = selectedFile.name;
    } else {
      imagePreview.style.display = "none";
      imagePreview.src = "#";
      fileUploadText.textContent = "Pilih File Gambar Baru...";
    }
  });

  btnVehicleIn.addEventListener("click", () => processVehicle("in"));
  btnVehicleOut.addEventListener("click", () => processVehicle("out"));
  btnRefreshData.addEventListener("click", fetchParkingData);

  async function processVehicle(actionType) {
    const formData = new FormData();
    formData.append("action_type", actionType);

    if (labeledImageSelect.value !== "none") {
      formData.append("labeled_image_name", labeledImageSelect.value);
    } else if (selectedFile) {
      formData.append("image_file", selectedFile);
    } else {
      setStatusMessage(
        "Harap unggah gambar atau pilih gambar terlabel.",
        "error"
      );
      return;
    }

    setStatusMessage("Memproses permintaan...", "loading");
    hideResults();

    try {
      const response = await fetch("/process_image/", {
        method: "POST",
        body: formData,
      });

      const result = await response.json(); // This is the final_response from backend

      if (!response.ok) {
        setStatusMessage(
          `Error: ${
            result.detail || result.message || "Terjadi kesalahan server."
          }`,
          "error"
        );
        // Even on error, Groq result might contain inference time if the error happened after Groq call
        if (
          result.groq_result &&
          result.groq_result.inference_time_seconds !== undefined
        ) {
          displayGroqResult(result.groq_result); // displayGroqResult will now also handle inference time
        }
        return;
      }

      if (result.status === "success") {
        setStatusMessage(result.message, "success");
      } else {
        setStatusMessage(result.message || "Gagal memproses.", "error");
      }

      // result.groq_result is where Plat_Nomor, Vehicle_Type, and inference_time_seconds are
      if (result.groq_result) {
        displayGroqResult(result.groq_result); // Pass the whole groq_result object
      }

      if (result.accuracy_info) {
        displayAccuracyResult(result.accuracy_info);
      }

      fetchParkingData();
    } catch (error) {
      console.error("Error processing vehicle:", error);
      setStatusMessage(`Terjadi kesalahan: ${error.message}`, "error");
    }
  }

  function setStatusMessage(message, type) {
    statusMessageDiv.textContent = message;
    statusMessageDiv.className = `status-message ${type}`;
  }

  function hideResults() {
    groqResultDiv.style.display = "none";
    accuracyResultDiv.style.display = "none";
    inferenceTimeSpan.textContent = "N/A"; // Reset inference time on hide
  }

  // Modified to handle inference time
  function displayGroqResult(groqData) {
    // groqData is now an object {Plat_Nomor, Vehicle_Type, inference_time_seconds}
    groqPlatSpan.textContent = groqData.Plat_Nomor || "N/A";
    groqTypeSpan.textContent = groqData.Vehicle_Type || "N/A";

    // Display inference time if available
    if (groqData.inference_time_seconds !== undefined) {
      inferenceTimeSpan.textContent = `${groqData.inference_time_seconds} detik`;
    } else {
      inferenceTimeSpan.textContent = "N/A";
    }
    // Make sure the accuracyResultDiv is shown if we are showing inference time
    // Assuming inference time is part of the "accuracy" display block.
    // If it's in groqResultDiv, then show that one.
    // Based on your HTML, it's in accuracyResultDiv
    accuracyResultDiv.style.display = "block"; // Or groqResultDiv if it's there
    groqResultDiv.style.display = "block"; // Show Groq specific details
  }

  function displayAccuracyResult(data) {
    if (data.message && !data.true_plate) {
      accuracyMessageSpan.textContent = data.message;
      plateAccuracySpan.textContent = "N/A";
      typeAccuracySpan.textContent = "N/A";
      overallAccuracySpan.textContent = "N/A";
      truePlatSpan.textContent = "N/A";
      trueTypeSpan.textContent = "N/A";
    } else {
      truePlatSpan.textContent = data.true_plate || "N/A";
      trueTypeSpan.textContent = data.true_type || "N/A";
      plateAccuracySpan.textContent =
        data.plate_accuracy !== undefined
          ? data.plate_accuracy.toFixed(2)
          : "N/A"; // Removed % here, add in HTML if needed
      typeAccuracySpan.textContent =
        data.type_accuracy !== undefined
          ? data.type_accuracy.toFixed(2)
          : "N/A"; // Removed % here
      overallAccuracySpan.textContent =
        data.overall_accuracy !== undefined
          ? data.overall_accuracy.toFixed(2)
          : "N/A"; // Removed % here
      accuracyMessageSpan.textContent = "";
    }
    // Inference time is now handled by displayGroqResult,
    // but we still need to show the accuracyResultDiv if accuracy data is present.
    accuracyResultDiv.style.display = "block";
  }

  async function fetchParkingData() {
    try {
      const response = await fetch("/parking_data");
      if (!response.ok) throw new Error("Gagal memuat data parkir");
      const data = await response.json();

      currentParkingTableBody.innerHTML = "";
      parkingHistoryTableBody.innerHTML = "";

      Object.values(data).forEach((vehicle) => {
        const originalPlat = vehicle.original_plat || vehicle.plat_nomor;

        if (vehicle.exit_time === null) {
          const row = currentParkingTableBody.insertRow();
          row.insertCell().textContent = originalPlat;
          row.insertCell().textContent = vehicle.vehicle_type;
          row.insertCell().textContent = vehicle.entry_time
            ? new Date(vehicle.entry_time).toLocaleString()
            : "N/A";
        } else {
          const row = parkingHistoryTableBody.insertRow();
          row.insertCell().textContent = originalPlat;
          row.insertCell().textContent = vehicle.vehicle_type;
          row.insertCell().textContent = vehicle.entry_time
            ? new Date(vehicle.entry_time).toLocaleString()
            : "N/A";
          row.insertCell().textContent = vehicle.exit_time
            ? new Date(vehicle.exit_time).toLocaleString()
            : "N/A";
          row.insertCell().textContent =
            vehicle.duration_minutes !== undefined
              ? vehicle.duration_minutes
              : "N/A";
          row.insertCell().textContent =
            vehicle.fee !== undefined
              ? vehicle.fee.toLocaleString("id-ID")
              : "N/A";
        }
      });
    } catch (error) {
      console.error("Error fetching parking data:", error);
      setStatusMessage("Gagal memuat data parkir.", "error");
    }
  }

  // Initial load
  loadLabeledImages();
  fetchParkingData();
});
