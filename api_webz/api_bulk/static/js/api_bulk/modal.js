function getCookie(name) {
    let cookieValue = null;

    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");

        for (let cookie of cookies) {
            cookie = cookie.trim();

            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
                break;
            }
        }
    }

    return cookieValue;
}


async function createBulkTask() {
  try {
    const data = await getBulkFormJSON();
    const csrfToken = getCookie("csrftoken");
    console.log("Sending task:", data);

    const response = await fetch("/bulk/create/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    console.log("Server response:", result);

    if (!response.ok) {
      throw new Error(result.error || "Failed to create task.");
    }

  } catch (error) {
    alert(error.message);
  }
}

async function getBulkFormJSON() {
  const taskName = document.getElementById("taskName").value.trim();
  const throttle = Number(document.getElementById("taskThrottle").value) || 0;
  const headersText = document.getElementById("taskHeaders").value.trim();
  const file = document.getElementById("taskFile").files[0];

  // Parse headers
  let headers = {};

  if (headersText) {
    try {
      headers = JSON.parse(headersText);
    } catch (error) {
      throw new Error("Headers must contain valid JSON.");
    }
  }

  // CSV is required
  if (!file) {
    throw new Error("Please select a CSV file.");
  }

  // Read CSV
  const csvText = await file.text();

  // Convert CSV → JSON
  const lines = csvText.trim().split(/\r?\n/);

  if (lines.length < 2) {
    throw new Error("CSV file is empty or contains no data.");
  }

  const columns = lines[0].split(",").map((column) => column.trim());

  const files = lines.slice(1).map((line) => {
    const values = line.split(",");

    const row = {};

    columns.forEach((column, index) => {
      row[column] = values[index]?.trim() || "";
    });

    return row;
  });

  // Final JSON
  return {
    task_name: taskName,
    throttle: throttle,
    headers: headers,
    csv_file: files,
  };
}
