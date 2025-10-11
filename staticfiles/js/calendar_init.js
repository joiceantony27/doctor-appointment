/**
 * Calendar initialization and time slot fetching for doctor appointment system
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeCalendarFunctionality();
    
    // Function to display toast messages
    window.showToast = function(type, message) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '5';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastElement = document.createElement('div');
        toastElement.id = toastId;
        toastElement.className = `toast align-items-center text-white ${getToastBgClass(type)}`;
        toastElement.setAttribute('role', 'alert');
        toastElement.setAttribute('aria-live', 'assertive');
        toastElement.setAttribute('aria-atomic', 'true');
        
        // Create toast content
        toastElement.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${getToastIcon(type)} ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add to container
        toastContainer.appendChild(toastElement);
        
        // Initialize and show the toast
        const toastInstance = new bootstrap.Toast(toastElement, {
            delay: 5000,
            autohide: true
        });
        
        toastInstance.show();
        
        // Remove from DOM after hiding
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    };
    
    // Helper functions for toast appearance
    function getToastBgClass(type) {
        switch(type) {
            case 'success': return 'bg-success';
            case 'warning': return 'bg-warning text-dark';
            case 'error': return 'bg-danger';
            case 'info': default: return 'bg-primary';
        }
    }
    
    function getToastIcon(type) {
        switch(type) {
            case 'success': return '<i class="fas fa-check-circle me-2"></i>';
            case 'warning': return '<i class="fas fa-exclamation-triangle me-2"></i>';
            case 'error': return '<i class="fas fa-exclamation-circle me-2"></i>';
            case 'info': default: return '<i class="fas fa-info-circle me-2"></i>';
        }
    }
});

// Function to initialize the calendar and time slot functionality
function initializeCalendarFunctionality() {
    console.log("Initializing calendar functionality");
    
    const calendarGrid = document.getElementById('calendarGrid');
    const timeSlotsContainer = document.getElementById('timeSlotsContainer');
    const timeSlotsGrid = document.getElementById('timeSlotsGrid');
    const currentMonthElement = document.getElementById('currentMonth');
    const prevMonthBtn = document.getElementById('prevMonth');
    const nextMonthBtn = document.getElementById('nextMonth');
    const selectedDayInput = document.getElementById('selectedDay');
    const selectedTimeSlotInput = document.getElementById('selectedTimeSlot');
    const doctorId = document.querySelector('.save-btn')?.dataset.doctorId;
    
    if (!calendarGrid || !currentMonthElement) {
        console.warn("Calendar elements not found, skipping initialization");
        return;
    }
    
    if (!doctorId) {
        console.error("Doctor ID not found, cannot fetch time slots");
        return;
    }
    
    console.log("Initializing calendar for doctor ID:", doctorId);
    
    let currentDate = new Date();
    let selectedDate = null;
    let selectedTimeSlot = null;
    
    // Initialize calendar
    function initializeCalendar() {
        console.log("Initializing calendar view");
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        // Set current month display
        currentMonthElement.textContent = new Date(year, month).toLocaleString('default', { month: 'long', year: 'numeric' });
        
        // Clear previous calendar
        calendarGrid.innerHTML = '';
        
        // Add day headers (Sun, Mon, etc.)
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        for (let i = 0; i < 7; i++) {
            const dayHeader = document.createElement('div');
            dayHeader.className = 'calendar-day-header';
            dayHeader.textContent = dayNames[i];
            calendarGrid.appendChild(dayHeader);
        }
        
        // Get first day of month
        const firstDay = new Date(year, month, 1).getDay();
        
        // Get days in month
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        // Get today's date for comparison
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        // Get available days from doctor's working hours
        let availableDays = [];
        const workingHoursByDay = {};
        
        // If doctor working hours are available, use them
        if (window.doctorWorkingHours && window.doctorWorkingHours.length) {
            console.log("Using doctor's working hours to determine available days");
            
            // Map day of week (0-6) to day name
            const mapDayOfWeekToName = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
            
            // Process working hours
            window.doctorWorkingHours.forEach(wh => {
                const dayName = wh.day_name || mapDayOfWeekToName[wh.day_of_week];
                if (dayName && !availableDays.includes(dayName)) {
                    availableDays.push(dayName);
                }
                
                // Store working hours by day
                workingHoursByDay[wh.day_of_week] = wh;
            });
            
            console.log("Available days from working hours:", availableDays);
        } else {
            // If no working hours defined, show all days as potentially available
            console.log("No doctor working hours found, showing all days as available");
            availableDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        }
        
        // Add empty cells for days before first day
        for (let i = 0; i < firstDay; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'calendar-day-empty';
            calendarGrid.appendChild(emptyCell);
        }
        
        // Add days
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(year, month, day);
            const dayOfWeek = date.toLocaleString('default', { weekday: 'long' });
            const dayElement = document.createElement('div');
            
            dayElement.className = 'calendar-day';
            dayElement.textContent = day;
            
            // Add tooltip with day name
            dayElement.title = dayOfWeek;
            
            // Check if this day is in the past
            const isPast = date < today;
            
            // Check if this day is available based on doctor's schedule
            const isDayAvailable = availableDays.includes(dayOfWeek);
            
            if (isPast) {
                // Past days are unavailable
                dayElement.classList.add('past');
                dayElement.title = "Past dates are not available for booking";
            } else if (!isDayAvailable) {
                // Days when doctor is not available - still show them but with different styling
                dayElement.classList.add('less-available');
                dayElement.title = `Doctor does not work on ${dayOfWeek}s`;
            } else {
                // Available days
                dayElement.classList.add('available');
                
                // Make this day selectable
                dayElement.addEventListener('click', function(event) {
                    selectDay(date, event);
                });
            }
            
            // If this is today, add a special class
            if (date.toDateString() === today.toDateString()) {
                dayElement.classList.add('today');
            }
            
            calendarGrid.appendChild(dayElement);
        }
    }
    
    // Select a day
    function selectDay(date, event) {
        console.log("Day selected:", date);
        selectedDate = date;
        
        // Format date in ISO format (YYYY-MM-DD) in the browser's local timezone
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        
        console.log("Formatted date for API:", formattedDate);
        selectedDayInput.value = formattedDate;
        
        // Update UI
        document.querySelectorAll('.calendar-day').forEach(function(day) {
            day.classList.remove('selected');
        });
        
        // Use currentTarget to ensure we're selecting the right element
        const currentTarget = event.currentTarget || event.target;
        currentTarget.classList.add('selected');
        
        // Show time slots container
        if (timeSlotsContainer) {
            timeSlotsContainer.style.display = 'block';
        }
        
        // Fetch time slots from API
        fetchTimeSlots(date);
    }
    
    // Fetch time slots from API
    function fetchTimeSlots(date) {
        // Format date in ISO format (YYYY-MM-DD)
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        
        console.log("Fetching time slots for date:", formattedDate);
        
        // Get day of week for the selected date (0-6, where 0 is Sunday)
        const dayOfWeek = date.getDay();
        // Convert to Django's day of week format (0-6, where 0 is Monday)
        const djangoDayOfWeek = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        
        console.log("Day of week for selected date:", dayOfWeek, "Django day of week:", djangoDayOfWeek);
        
        const url = `/appointments/api/doctors/${doctorId}/time-slots/?date=${formattedDate}&day_of_week=${dayOfWeek}&js_format=true`;
        console.log("Fetching time slots from URL:", url);
        
        // Clear previous selection
        selectedTimeSlot = null;
        if (selectedTimeSlotInput) {
            selectedTimeSlotInput.value = '';
        }
        
        // Show loading state with spinner
        if (timeSlotsGrid) {
            timeSlotsGrid.innerHTML = `
                <div class="time-slots-loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="loading-text">
                        <div class="mb-1">Loading available time slots...</div>
                        <div class="small text-muted">This will only take a moment</div>
                    </div>
                </div>
            `;
        }
        
        // Get CSRF token for AJAX request
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Fetch time slots from the API with proper error handling
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin' // Include cookies for authentication
        })
        .then(response => {
            if (!response.ok) {
                // Handle HTTP errors
                console.error("Error response:", response.status, response.statusText);
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Time slots data:", data);
            
            // Check for explicit error from server
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Show success message if there's a message from server
            if (data.message && !data.error && window.showToast) {
                window.showToast('info', data.message);
            }
            
            // Process time slots from the response
            let timeSlots = data.time_slots || [];
            const bookedSlots = data.booked_slots || [];
            const doctorSchedule = data.doctor_schedule || null;
            
            // Show doctor's schedule information if available
            if (doctorSchedule && timeSlotsGrid) {
                const scheduleInfo = document.createElement('div');
                scheduleInfo.className = 'alert alert-info mb-3';
                scheduleInfo.innerHTML = `
                    <i class="fas fa-calendar-alt me-2"></i>
                    <strong>Doctor's Schedule:</strong> ${doctorSchedule.day} - ${doctorSchedule.start_time} to ${doctorSchedule.end_time}
                `;
                timeSlotsGrid.innerHTML = '';
                timeSlotsGrid.appendChild(scheduleInfo);
            }
            
            // If no doctor schedule for this day, show a message
            if (data.no_schedule && timeSlotsGrid) {
                timeSlotsGrid.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <i class="far fa-calendar-times"></i>
                        </div>
                        <div class="empty-state-text">
                            The doctor is not available on ${data.day}
                        </div>
                        <div class="empty-state-subtext">
                            Please select another date from the calendar
                        </div>
                    </div>
                `;
                return;
            }
            
            if (timeSlots.length > 0 && timeSlotsGrid) {
                // Add a success message
                const successDiv = document.createElement('div');
                successDiv.className = 'alert alert-success mb-3';
                successDiv.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>
                    Available slots found for ${data.day}, ${data.date}
                `;
                timeSlotsGrid.innerHTML = '';
                timeSlotsGrid.appendChild(successDiv);
                
                // Display the time slots
                displayTimeSlots(timeSlots, bookedSlots, date);
            } else if (timeSlotsGrid) {
                // Show empty state when no time slots are available
                timeSlotsGrid.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <i class="far fa-calendar-times"></i>
                        </div>
                        <div class="empty-state-text">
                            No time slots available for this date
                        </div>
                        <div class="empty-state-subtext">
                            Please select another date or contact the doctor directly
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error("Error fetching time slots:", error);
            
            // Show an error message to the user
            if (timeSlotsGrid) {
                timeSlotsGrid.innerHTML = `
                    <div class="alert alert-danger">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-exclamation-circle me-3" style="font-size: 1.5rem;"></i>
                            <div>
                                <div class="fw-bold">Could not fetch doctor's schedule</div>
                                <div>${error.message || "Server error occurred. Please try again later."}</div>
                            </div>
                        </div>
                        <button class="btn btn-sm btn-outline-danger mt-2" onclick="fetchTimeSlots(selectedDate)">
                            <i class="fas fa-sync-alt me-1"></i> Try Again
                        </button>
                    </div>
                `;
            }
            
            if (window.showToast) {
                window.showToast('error', "Failed to load time slots. Please try again.");
            }
        });
    }
    
    // Display time slots
    function displayTimeSlots(timeSlots, bookedSlots = [], selectedDate) {
        if (!timeSlotsGrid) return;
        
        // Create a container for time slots if it doesn't exist
        let timeSlotsWrapper = document.querySelector('.time-slots-wrapper');
        if (!timeSlotsWrapper) {
            timeSlotsWrapper = document.createElement('div');
            timeSlotsWrapper.className = 'time-slots-wrapper';
            timeSlotsGrid.appendChild(timeSlotsWrapper);
        } else {
            timeSlotsWrapper.innerHTML = '';
        }
        
        // If we have time slots, display them
        if (timeSlots && timeSlots.length > 0) {
            // Sort time slots chronologically
            timeSlots.sort((a, b) => {
                return a.start_time.localeCompare(b.start_time);
            });
            
            // Check if selected date is today
            const today = new Date();
            const isToday = selectedDate.getDate() === today.getDate() && 
                           selectedDate.getMonth() === today.getMonth() && 
                           selectedDate.getFullYear() === today.getFullYear();
            
            // Get current time for comparison
            const currentHour = today.getHours();
            const currentMinute = today.getMinutes();
            
            // Create a helper function to check if a time slot is before current time
            const isBeforeCurrentTime = (timeString) => {
                if (!isToday) return false;
                
                const [hours, minutes] = timeString.split(':').map(part => parseInt(part, 10));
                
                // Calculate current time plus 30 minutes buffer
                let bufferDate = new Date(today);
                bufferDate.setMinutes(bufferDate.getMinutes() + 30);
                const bufferHour = bufferDate.getHours();
                const bufferMinute = bufferDate.getMinutes();
                
                // Return true if the slot time is before the buffer time
                return (hours < bufferHour) || (hours === bufferHour && minutes < bufferMinute);
            };
            
            // Process time slots to mark those before current time as unavailable
            if (isToday) {
                timeSlots.forEach(slot => {
                    if (isBeforeCurrentTime(slot.start_time) && slot.available) {
                        slot.available = false;
                        slot.reason = "This time slot has already passed";
                    }
                });
            }
            
            // Check if there are any available slots
            const hasAvailableSlots = timeSlots.some(slot => slot.available === true);
            
            if (!hasAvailableSlots) {
                timeSlotsWrapper.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        No available time slots for this day. Please select another date.
                    </div>
                `;
                return;
            }
            
            // Add a helper text for the 30-minute intervals
            const helperText = document.createElement('div');
            helperText.className = 'mb-3 text-muted small';
            helperText.innerHTML = `<i class="fas fa-info-circle me-2"></i>All time slots are 30 minutes in duration.`;
            timeSlotsWrapper.appendChild(helperText);
            
            // If it's today, add a note about past time slots and buffer
            if (isToday) {
                // Calculate buffer time for display
                let bufferDate = new Date(today);
                bufferDate.setMinutes(bufferDate.getMinutes() + 30);
                const bufferHour = bufferDate.getHours();
                const bufferMinute = bufferDate.getMinutes();
                
                // Format hours for 12-hour display
                const display12Hour = bufferHour > 12 ? bufferHour - 12 : bufferHour === 0 ? 12 : bufferHour;
                const amPm = bufferHour >= 12 ? 'PM' : 'AM';
                
                const todayNote = document.createElement('div');
                todayNote.className = 'alert alert-info mb-3';
                todayNote.innerHTML = `
                    <i class="fas fa-clock me-2"></i>
                    You've selected today. Time slots before ${display12Hour}:${String(bufferMinute).padStart(2, '0')} ${amPm} are not available for booking (includes 30-minute preparation time).
                `;
                timeSlotsWrapper.appendChild(todayNote);
            }
            
            // Create a slot grid container
            const slotGrid = document.createElement('div');
            slotGrid.className = 'time-slots-grid';
            timeSlotsWrapper.appendChild(slotGrid);
            
            // Group slots by hour for better organization
            const slotsByHour = {};
            timeSlots.forEach(slot => {
                const hour = parseInt(slot.start_time.split(':')[0], 10);
                if (!slotsByHour[hour]) {
                    slotsByHour[hour] = [];
                }
                slotsByHour[hour].push(slot);
            });
            
            // Sort hours
            const sortedHours = Object.keys(slotsByHour).sort((a, b) => parseInt(a) - parseInt(b));
            
            // Create hour sections
            sortedHours.forEach(hour => {
                const hourSlots = slotsByHour[hour];
                
                // Create hour section
                const hourSection = document.createElement('div');
                hourSection.className = 'hour-section mb-3';
                
                // Hour heading with formatted time (12-hour format with AM/PM)
                const displayHour = parseInt(hour) % 12 || 12;
                const amPm = parseInt(hour) >= 12 ? 'PM' : 'AM';
                
                const hourHeading = document.createElement('h6');
                hourHeading.className = 'hour-heading';
                hourHeading.innerHTML = `<i class="far fa-clock me-2"></i>${displayHour}:00 ${amPm}`;
                hourSection.appendChild(hourHeading);
                
                // Hour grid for the slots
                const hourGrid = document.createElement('div');
                hourGrid.className = 'hour-slots-grid';
                hourSection.appendChild(hourGrid);
                
                // Add slots to the hour grid
                hourSlots.forEach(function(slot) {
                    const slotElement = document.createElement('div');
                    
                    // Check if this slot is available
                    const isAvailable = slot.available === true;
                    const reason = slot.reason || "This slot is unavailable";
                    
                    // Format the display for readability - show AM/PM format
                    const startTimeParts = slot.start_time.split(':');
                    const endTimeParts = slot.end_time.split(':');
                    const startHour = parseInt(startTimeParts[0], 10);
                    const startMinute = startTimeParts[1];
                    const endHour = parseInt(endTimeParts[0], 10);
                    const endMinute = endTimeParts[1];
                    
                    const startAmPm = startHour >= 12 ? 'PM' : 'AM';
                    const endAmPm = endHour >= 12 ? 'PM' : 'AM';
                    
                    const displayStartHour = startHour > 12 ? startHour - 12 : startHour === 0 ? 12 : startHour;
                    const displayEndHour = endHour > 12 ? endHour - 12 : endHour === 0 ? 12 : endHour;
                    
                    // Formatted time display
                    const timeDisplay = `${displayStartHour}:${startMinute} ${startAmPm} - ${displayEndHour}:${endMinute} ${endAmPm}`;
                    
                    if (!isAvailable) {
                        // Handle unavailable slots
                        slotElement.className = 'time-slot unavailable';
                        
                        // Check if it's a past slot (today) or a booked slot
                        if (reason === "This time slot has already passed") {
                            slotElement.classList.add('past');
                        } else {
                            slotElement.classList.add('booked');
                        }
                        
                        slotElement.innerHTML = `<span>${timeDisplay}</span>`;
                        slotElement.dataset.startTime = slot.start_time;
                        slotElement.dataset.endTime = slot.end_time;
                        
                        // Add tooltip with unavailability reason
                        slotElement.title = reason;
                        
                        // Add click handler for unavailable slots to show reason
                        slotElement.addEventListener('click', function() {
                            if (window.showToast) {
                                window.showToast('warning', reason);
                            }
                        });
                    } else {
                        // Handle available slots
                        slotElement.className = 'time-slot available';
                        slotElement.innerHTML = `<span>${timeDisplay}</span>`;
                        slotElement.dataset.startTime = slot.start_time;
                        slotElement.dataset.endTime = slot.end_time;
                        slotElement.title = "Click to select this time slot";
                        
                        // Add click event for available slots
                        slotElement.addEventListener('click', function(event) {
                            selectTimeSlot(slot, event);
                        });
                    }
                    
                    hourGrid.appendChild(slotElement);
                });
                
                // Only add hours that have at least one available slot
                const hasAvailableSlots = hourSlots.some(slot => slot.available);
                if (hasAvailableSlots) {
                    slotGrid.appendChild(hourSection);
                }
            });
            
            // Add a color legend
            const legendContainer = document.createElement('div');
            legendContainer.className = 'slot-legend mt-3';
            legendContainer.innerHTML = `
                <div class="d-flex justify-content-center flex-wrap gap-3">
                    <div class="legend-item">
                        <span class="legend-color bg-success"></span>
                        <span class="legend-text">Available</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color bg-secondary"></span>
                        <span class="legend-text">Booked</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color bg-warning"></span>
                        <span class="legend-text">Selected</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color bg-danger"></span>
                        <span class="legend-text">Past</span>
                    </div>
                </div>
            `;
            
            // Add the legend to the time slots wrapper
            timeSlotsWrapper.appendChild(legendContainer);
        } else {
            // If no time slots available
            timeSlotsWrapper.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    No time slots available for this day. Please select another date.
                </div>
            `;
        }
    }
    
    // Select time slot
    function selectTimeSlot(slot, event) {
        console.log("Time slot selected:", slot);
        selectedTimeSlot = slot;
        
        // Get the element that was clicked
        const slotElement = event.target.closest ? event.target.closest('.time-slot') : event.target;
        
        // Get the actual time values from the slot or from the element's dataset
        let startTime = slotElement.dataset.startTime || slot.start_time;
        let endTime = slotElement.dataset.endTime || slot.end_time;
        
        // Format the time slot value as "startTime-endTime" (e.g. "09:00-09:30")
        const timeSlotValue = `${startTime}-${endTime}`;
        console.log("Time slot value:", timeSlotValue);
        
        // Set the hidden input value
        if (selectedTimeSlotInput) {
            selectedTimeSlotInput.value = timeSlotValue;
        }
        
        // Update UI
        document.querySelectorAll('.time-slot').forEach(function(el) {
            el.classList.remove('selected');
        });
        
        // Add selected class to the clicked element
        slotElement.classList.add('selected');
        
        // Show a success toast for better UX
        const timeText = slotElement.innerText.trim();
        if (window.showToast) {
            window.showToast('success', `Selected time slot: ${timeText}`);
        }
        
        // Update appointment summary if function exists
        if (typeof updateAppointmentSummary === 'function') {
            updateAppointmentSummary();
        }
        
        // Smooth scroll to the appointment type section
        const appointmentTypesContainer = document.querySelector('.appointment-types-container');
        if (appointmentTypesContainer) {
            appointmentTypesContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    // Initialize calendar
    initializeCalendar();
    
    // Handle month navigation
    if (prevMonthBtn) {
        prevMonthBtn.addEventListener('click', function() {
            currentDate.setMonth(currentDate.getMonth() - 1);
            initializeCalendar();
        });
    }
    
    if (nextMonthBtn) {
        nextMonthBtn.addEventListener('click', function() {
            currentDate.setMonth(currentDate.getMonth() + 1);
            initializeCalendar();
        });
    }
} 