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

  const currentParkingTableBody = document.querySelector(
    "#currentParkingTable tbody"
  );
  const parkingHistoryTableBody = document.querySelector(
    "#parkingHistoryTable tbody"
  );

  let selectedFile = null;

  // Load labeled images for selection
  async function loadLabeledImages() {
    try {
      const response = await fetch("/labeled_images");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      data.images.forEach((imgPath) => {
        const option = document.createElement("option");
        option.value = imgPath; // e.g., choosenCar/car1.jpg
        option.textContent = imgPath.split("/").pop(); // e.g., car1.jpg
        labeledImageSelect.appendChild(option);
      });
    } catch (error) {
      console.error("Error loading labeled images:", error);
      setStatusMessage("Gagal memuat daftar gambar berlabel.", "error");
    }
  }

  labeledImageSelect.addEventListener("change", () => {
    if (labeledImageSelect.value !== "none") {
      imagePreview.src = `/${labeledImageSelect.value}`; // Prepend / to make it root relative
      imagePreview.style.display = "block";
      selectedFile = null; // Clear any manually uploaded file
      imageUpload.value = ""; // Clear file input
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
      labeledImageSelect.value = "none"; // Deselect labeled image if new one is uploaded
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

      const result = await response.json();

      if (!response.ok) {
        // HTTP errors like 400, 404, 500
        setStatusMessage(
          `Error: ${
            result.detail || result.message || "Terjadi kesalahan server."
          }`,
          "error"
        );
        if (result.groq_result) displayGroqResult(result.groq_result); // Show Groq if available
        return;
      }

      // Handle application-level success/error from our backend logic
      if (result.status === "success") {
        setStatusMessage(result.message, "success");
      } else {
        setStatusMessage(result.message || "Gagal memproses.", "error");
      }

      if (result.groq_result) {
        displayGroqResult(result.groq_result);
      }

      if (result.accuracy_info) {
        displayAccuracyResult(result.accuracy_info);
      }

      fetchParkingData(); // Refresh tables
    } catch (error) {
      console.error("Error processing vehicle:", error);
      setStatusMessage(`Terjadi kesalahan: ${error.message}`, "error");
    }
  }

  function setStatusMessage(message, type) {
    statusMessageDiv.textContent = message;
    statusMessageDiv.className = `status-message ${type}`; // 'success', 'error', 'loading'
  }

  function hideResults() {
    groqResultDiv.style.display = "none";
    accuracyResultDiv.style.display = "none";
  }

  function displayGroqResult(data) {
    groqPlatSpan.textContent = data.Plat_Nomor || "N/A";
    groqTypeSpan.textContent = data.Vehicle_Type || "N/A";
    groqResultDiv.style.display = "block";
  }

  function displayAccuracyResult(data) {
    if (data.message && !data.true_plate) {
      // If only a message (e.g. label not found)
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
          : "N/A";
      typeAccuracySpan.textContent =
        data.type_accuracy !== undefined
          ? data.type_accuracy.toFixed(2)
          : "N/A";
      overallAccuracySpan.textContent =
        data.overall_accuracy !== undefined
          ? data.overall_accuracy.toFixed(2)
          : "N/A";
      accuracyMessageSpan.textContent = ""; // Clear message if full data is present
    }
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
        const originalPlat = vehicle.original_plat || vehicle.plat_nomor; // Use original if available

        if (vehicle.exit_time === null) {
          // Currently parked
          const row = currentParkingTableBody.insertRow();
          row.insertCell().textContent = originalPlat;
          row.insertCell().textContent = vehicle.vehicle_type;
          row.insertCell().textContent = vehicle.entry_time
            ? new Date(vehicle.entry_time).toLocaleString()
            : "N/A";
        } else {
          // Exited
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
