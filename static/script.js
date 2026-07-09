/* script.js */

const entriesFetchedSpan = document.getElementById("entriesFetched");

function updateEntriesFetchedDisplay(value) {
  entriesFetchedSpan.textContent = value;
}

function startScraping() {
  if (scrapingActive) {
    setScraperNotice("Scraping is already running.");
    return;
  }

  fetch("/start_scrape", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      setScraperNotice(data.message);
      scrapingActive = data.scraping_active; // Use server's response
      updateScraperUI(data.current_run);
      if (data.last_scrape_time) {
        // Update last scrape time after start
        updateLastScrapeTimeDisplay(data.last_scrape_time);
      }
      updateScrapingStatusDisplay();
    })
    .catch((error) => {
      console.error("Error starting scraping:", error);
      setScraperNotice("Error starting scraping. Check console for details.", true);
    });
}

function stopScraping() {
  if (!scrapingActive) {
    setScraperNotice("Scraping is not currently running.");
    return;
  }

  fetch("/stop_scrape", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      setScraperNotice(data.message);
      scrapingActive = data.scraping_active; // Use server's response
      updateScraperUI(data.current_run);
      if (data.last_scrape_time) {
        // Update last scrape time after stop
        updateLastScrapeTimeDisplay(data.last_scrape_time);
      }
      updateScrapingStatusDisplay();
    })
    .catch((error) => {
      console.error("Error stopping scraping:", error);
      setScraperNotice("Error stopping scraping. Check console for details.", true);
    });
}

function updateScrapingStatusDisplay() {
  fetch("/scrape_status")
    .then((response) => response.json())
    .then((data) => {
      scrapingActive = data.scraping_active; // Update scrapingActive from server status
      updateScraperUI(data.current_run); // Call updateUI function
      if (data.last_scrape_time) {
        // Update last scrape time on status update
        updateLastScrapeTimeDisplay(data.last_scrape_time);
      }
    })
    .catch((error) => {
      console.error("Error fetching scraping status:", error);
    });
}

function updateScraperUI(currentRun = null) {
  // NEW FUNCTION to update UI elements based on scrapingActive
  if (scrapingActive) {
    document.getElementById("startButton").disabled = true;
    document.getElementById("stopButton").disabled = false;
  } else {
    document.getElementById("startButton").disabled = false;
    document.getElementById("stopButton").disabled = true;
  }

  renderScraperRun(currentRun);
}

function renderScraperRun(currentRun) {
  const statusElement = document.getElementById("scrapingStatus");
  const status = currentRun?.status || (scrapingActive ? "running" : "idle");
  const statusLabel = formatStatusLabel(status);

  if (statusElement) {
    statusElement.textContent = statusLabel;
    statusElement.className = `scraper-status-badge ${statusClassName(status)}`;
  }

  setText("scraperCity", currentRun?.city || "-");
  setText("scraperKeyword", currentRun?.search_keyword || "-");
  setText("scraperPage", currentRun?.page_number ?? "-");
  setText("scraperSaved", currentRun?.saved_count ?? 0);
  setText("scraperSkipped", currentRun?.skipped_count ?? 0);
  setText("scraperDuplicates", currentRun?.duplicate_count ?? 0);
  setText("scraperStartedAt", formatDateTime(currentRun?.started_at));
  setText("scraperFinishedAt", formatDateTime(currentRun?.finished_at));

  const errorElement = document.getElementById("scraperError");
  if (!errorElement) return;

  if (currentRun?.error_message) {
    errorElement.textContent = currentRun.error_message;
    errorElement.classList.remove("hidden");
  } else {
    errorElement.textContent = "";
    errorElement.classList.add("hidden");
  }
}

function setText(elementId, value) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = value;
  }
}

function setScraperNotice(message, isError = false) {
  const notice = document.getElementById("scraperNotice");
  if (!notice) return;

  notice.textContent = message || "";
  notice.classList.toggle("text-red-600", isError);
  notice.classList.toggle("text-gray-500", !isError);
}

function formatStatusLabel(status) {
  const labels = {
    running: "Running",
    success: "Success",
    failed: "Failed",
    stopped: "Stopped",
    idle: "Not running",
    completed: "Completed",
  };

  return labels[status] || "Not running";
}

function statusClassName(status) {
  const classes = {
    running: "status-running",
    success: "status-success",
    failed: "status-failed",
    stopped: "status-stopped",
    completed: "status-success",
    idle: "status-idle",
  };

  return classes[status] || "status-idle";
}

function formatDateTime(value) {
  if (!value) return "-";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";

  return date.toLocaleString();
}

function clearFilters() {
  document.getElementById("firstNameFilter").value = "";
  document.getElementById("lastNameFilter").value = "";
  document.getElementById("cityFilter").value = "";
  document.getElementById("provinceFilter").value = "";
  refreshObituaries();
}

document.addEventListener("DOMContentLoaded", function () {
  refreshObituaries();
  // updateDashboardSummary(); // If you still use this
  updateScrapingStatusDisplay(); // Initial status update on load
  setInterval(updateScrapingStatusDisplay, 20000);

  document
    .getElementById("filterForm")
    .addEventListener("submit", function (event) {
      event.preventDefault();
      applyFilters();
    });

  const tagForm = document.getElementById("tagUpdateForm");
  if (tagForm) {
    tagForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const formData = new FormData(this);
      const obituaryId = this.dataset.obituaryId;

      fetch(`/update_tags/${obituaryId}`, {
        method: "POST",
        body: formData,
      })
        .then((response) => {
          if (response.ok) {
            window.location.reload();
          } else {
            alert("Error updating tag");
          }
        })
        .catch((error) => console.error("Error:", error));
    });
  }
});

function applyFilters() {
  // Retrieve filter input values
  const firstName = document.getElementById("firstNameFilter").value.trim();
  const lastName = document.getElementById("lastNameFilter").value.trim();
  const city = document.getElementById("cityFilter").value.trim();
  const province = document.getElementById("provinceFilter").value.trim();

  // Show loading spinner
  document.getElementById("loading-spinner").classList.remove("hidden");
  document.getElementById("obituaryAccordionContainer").innerHTML = ""; // Clear accordion container instead of obituaryList
  document.getElementById("noNewEntries").classList.add("hidden");

  // Build query parameters dynamically
  const params = new URLSearchParams();
  if (firstName) params.append("firstName", firstName);
  if (lastName) params.append("lastName", lastName);
  if (city) params.append("city", city);
  if (province) params.append("province", province);

  fetch(`/search_obituaries?${params.toString()}`)
    .then((response) => response.json())
    .then((data) => {
      // Hide loading spinner
      document.getElementById("loading-spinner").classList.add("hidden");

      if (data.length === 0) {
        document.getElementById("noNewEntries").classList.remove("hidden"); // Show no entries message
      } else {
        document.getElementById("noNewEntries").classList.add("hidden"); // Hide no entries message
        renderYearAccordion(data); // Render accordion with filtered data, now YEAR accordion
      }
      if (window.renderMapObituaries) {
        window.renderMapObituaries(data);
      }
    })
    .catch((error) => {
      console.error("Search error:", error);
      alert("Error fetching search results.");
      // Hide loading spinner on error
      document.getElementById("loading-spinner").classList.add("hidden");
    });
}

function refreshObituaries() {
  // Modified refreshObituaries to use year accordion
  document.getElementById("loading-spinner").classList.remove("hidden");
  document.getElementById("obituaryAccordionContainer").innerHTML = ""; // Clear previous accordion
  document.getElementById("noNewEntries").classList.add("hidden");

  fetch("/get_obituaries")
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("loading-spinner").classList.add("hidden");

      if (data.length === 0) {
        document.getElementById("noNewEntries").classList.remove("hidden");
      } else {
        document.getElementById("noNewEntries").classList.add("hidden");
        renderYearAccordion(data); // Call function to render YEAR accordion
      }
      if (window.renderMapObituaries) {
        window.renderMapObituaries(data);
      }
    })
    .catch((error) => {
      console.error("Error refreshing obituaries:", error);
      document.getElementById("loading-spinner").classList.add("hidden");
    });
}

function renderYearAccordion(obituaries) {
  // Renamed function to render YEAR accordion
  const accordionContainer = document.getElementById(
    "obituaryAccordionContainer",
  );
  const yearGroups = groupObituariesByYear(obituaries); // Group data by year (new function below)
  const yearOrder = ["2026", "2025", "2024", "2023", "2022", "Before 2022"]; // Define year order
  let firstAccordionSection = true; // Flag to track the first accordion

  yearOrder.forEach((year) => {
    // Use yearOrder to control the order of accordion sections
    if (yearGroups.hasOwnProperty(year)) {
      const yearObituaries = yearGroups[year];
      if (yearObituaries.length > 0) {
        // Only create accordion if there are obituaries for the year
        const yearAccordion = createYearAccordionSection(
          year,
          yearObituaries,
          firstAccordionSection,
        ); // Create year accordion section (new function below), pass firstAccordionSection
        accordionContainer.appendChild(yearAccordion);
        if (firstAccordionSection) {
          firstAccordionSection = false; // Set flag to false after creating the first section
        }
      }
    }
  });
}

function groupObituariesByYear(obituaries) {
  // NEW function to group by YEAR
  const yearGroups = {
    // Initialize with all year groups to maintain order and include empty groups
    2026: [],
    2025: [],
    2024: [],
    2023: [],
    2022: [],
    "Before 2022": [],
  };

  obituaries.forEach((obituary) => {
    let publicationYear = "Unknown Year"; // Default year if extraction fails
    if (obituary.publication_date) {
      const year = new Date(obituary.publication_date).getFullYear();
      if (!isNaN(year)) {
        // Check if year is a valid number
        publicationYear = String(year); // Convert year to string for grouping
      } else {
        publicationYear = "Unknown Year";
      }
    }

    if (publicationYear === "2026") yearGroups["2026"].push(obituary);
    else if (publicationYear === "2025") yearGroups["2025"].push(obituary);
    else if (publicationYear === "2024") yearGroups["2024"].push(obituary);
    else if (publicationYear === "2023") yearGroups["2023"].push(obituary);
    else if (publicationYear === "2022") yearGroups["2022"].push(obituary);
    else if (
      publicationYear !== "Unknown Year" &&
      parseInt(publicationYear) < 2022
    )
      yearGroups["Before 2022"].push(obituary);
    // else yearGroups["Unknown Year"].push(obituary); // Optional: Handle 'Unknown Year' if needed, or just ignore
  });
  return yearGroups;
}

function createYearAccordionSection(year, obituaries, isFirstSection) {
  // NEW function to create YEAR accordion section, added isFirstSection parameter
  const yearSection = document.createElement("div");
  yearSection.classList.add("accordion-section"); // You can keep 'accordion-section' class for styling

  const yearHeading = document.createElement("button");
  yearHeading.classList.add("accordion-button"); // Keep 'accordion-button' class for styling
  yearHeading.textContent = year; // Set the year as the button text
  yearHeading.addEventListener("click", () => {
    // Accordion toggle functionality (same as before)
    yearContent.classList.toggle("hidden");
    yearHeading.classList.toggle("active"); // Toggle active class on header
  });
  yearSection.appendChild(yearHeading);

  const yearContent = document.createElement("div");
  yearContent.classList.add("accordion-content"); // Keep 'accordion-content' class
  if (!isFirstSection) {
    // Add 'hidden' class only if it's NOT the first section
    yearContent.classList.add("hidden");
  }

  // Create the table
  const obituaryTable = document.createElement("table");
  obituaryTable.classList.add("obituary-table"); // Keep 'obituary-table' class for table styling

  // Create table header (<thead>)
  const tableHeader = document.createElement("thead");
  tableHeader.innerHTML = `
        <tr>
            <th class="border px-4 py-2">Name</th>
            <th class="border px-4 py-2">City</th>
            <th class="border px-4 py-2">Province</th>
            <th class="border px-4 py-2">Birth Date</th>
            <th class="border px-4 py-2">Death Date</th>
            <th class="border px-4 py-2">View</th>
        </tr>
    `;
  obituaryTable.appendChild(tableHeader);

  // Create a paragraph for "No obituaries in this year" if obituaries array is empty
  if (!obituaries || obituaries.length === 0) {
    const noObituariesPara = document.createElement("p");
    noObituariesPara.textContent = "No obituaries in this year.";
    yearContent.appendChild(noObituariesPara);
    yearSection.appendChild(yearContent);
    return yearSection; // Return early if no obituaries
  }

  // Create table body (<tbody>)
  const tableBody = document.createElement("tbody");
  obituaries.forEach((obituary) => {
    const row = document.createElement("tr");
    row.classList.add("hover:bg-gray-100", "transition");

    // Construct Name cell content to include pill BEFORE the name
    let nameCellContent = `<td class="border px-4 py-2">`; // Start of td

    if (obituary.tags === "new") {
      nameCellContent += `
                    <span class="inline-flex items-center justify-center px-2 py-1 mr-2 text-xs font-bold leading-none text-white bg-blue-500 rounded-full">
                        New
                    </span>`; // New Pill
    } else if (obituary.tags === "updated") {
      nameCellContent += `
                    <span class="inline-flex items-center justify-center px-2 py-1 mr-2 text-xs font-bold leading-none text-white bg-gray-500 rounded-full">
                        Updated
                    </span>`; // Updated Pill (Gray color)
    }
    nameCellContent += `
                <a href="/obituary/${obituary.id}" class="font-medium text-gray-700 hover:text-blue-600 inline-flex items-center">
                    ${obituary.first_name || "N/A"} ${obituary.last_name || "N/A"}
                </a></td>`; // Name Link

    row.innerHTML = `
            ${nameCellContent}
            <td class="border px-4 py-2">${obituary.city || "N/A"}</td>
            <td class="border px-4 py-2">${obituary.province || "N/A"}</td>
            <td class="border px-4 py-2">${obituary.birth_date || "N/A"}</td>
            <td class="border px-4 py-2">${obituary.death_date || "N/A"}</td>
            <td class="border px-4 py-2">
                <a href="/obituary/${obituary.id}" class="text-blue-500 hover:underline">🔗 View</a>
            </td>
        `;
    tableBody.appendChild(row);
  });
  obituaryTable.appendChild(tableBody);
  yearContent.appendChild(obituaryTable);
  yearSection.appendChild(yearContent);

  if (isFirstSection) {
    yearHeading.classList.add("active");
  }

  return yearSection;
}

function updateLastScrapeTimeDisplay(timeString) {
  // NEW function to update last scrape time
  const lastScrapeTimeSpan = document.getElementById("lastScrapeTimeDisplay");
  if (timeString) {
    const formattedTime = new Date(timeString).toLocaleString();
    lastScrapeTimeSpan.textContent = formattedTime;
  } else {
    lastScrapeTimeSpan.textContent = "Never";
  }
}
