const semesterFiles = [
  { key: 'spring26', path: 'semesters/spring26.json' },
  { key: 'fall25', path: 'semesters/fall25.json' }
];

let colors = null;
let currentSemester = null;
let hasFinal = true;
let eventDays = {
  lecture: new Set(),
  lab: new Set(),
  recitation: new Set()
};

document.addEventListener('DOMContentLoaded', async () => {
  // Load colors
  try {
    colors = await fetchJSON('theme/colors.json');
  } catch (e) {
    console.error('Failed to load colors.json:', e);
  }

  // Populate semester select
  const select = document.getElementById('semesterSelect');
  for (const sem of semesterFiles) {
    const option = document.createElement('option');
    option.value = sem.path;
    option.textContent = sem.key;
    select.appendChild(option);
  }

  select.addEventListener('change', async (e) => {
    if (e.target.value) {
      await loadSemester(e.target.value);
    }
  });

  // Auto-load first semester
  if (semesterFiles.length > 0) {
    select.value = semesterFiles[0].path;
    await loadSemester(semesterFiles[0].path);
  }

  // Day matrix toggle logic
  document.querySelectorAll('.day-matrix .day-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const row = btn.closest('tr');
      const eventType = row.dataset.event;
      const day = btn.dataset.day;
      btn.classList.toggle('active');
      if (btn.classList.contains('active')) {
        eventDays[eventType].add(day);
      } else {
        eventDays[eventType].delete(day);
      }
      renderSchedule();
    });
  });

  // Has Final toggle logic
  document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      hasFinal = btn.dataset.value === 'yes';
      console.log('Toggle clicked, hasFinal now:', hasFinal);
      renderSchedule();
    });
  });
});

async function loadSemester(path) {
  try {
    currentSemester = await fetchJSON(path);
    const select = document.getElementById('semesterSelect');
    select.options[select.selectedIndex].textContent = currentSemester.name;
    renderSchedule();
  } catch (err) {
    console.error('Failed to load semester:', err);
    alert('Failed to load semester: ' + err.message);
  }
}

async function fetchJSON(path) {
  console.log('Fetching:', path);
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  const data = await response.json();
  console.log('Loaded:', path);
  return data;
}

function generateWeeks(firstMonday, lastClassDate) {
  const weeks = [];
  let current = new Date(firstMonday + 'T00:00:00');
  const end = new Date(lastClassDate + 'T00:00:00');
  let weekNum = 1;

  // Validate firstMonday is actually a Monday (0=Sun, 1=Mon, ...)
  if (current.getDay() !== 1) {
    const dayName = current.toLocaleDateString('en-US', { weekday: 'long' });
    console.error(`firstMonday (${firstMonday}) is a ${dayName}, not Monday!`);
    alert(`Warning: firstMonday (${firstMonday}) is a ${dayName}, not Monday!`);
  }

  while (current <= end) {
    const week = { number: weekNum, days: [] };
    for (let i = 0; i < 5; i++) {
      const day = new Date(current);
      day.setDate(day.getDate() + i);
      week.days.push({
        dateStr: day.toISOString().split('T')[0],
        display: day.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      });
    }
    weeks.push(week);
    current.setDate(current.getDate() + 7);
    weekNum++;
  }
  return weeks;
}

function getHoliday(dateStr) {
  if (!currentSemester?.holidays) return null;
  return currentSemester.holidays.find(h => h.date === dateStr);
}

function isInSpringBreak(dateStr) {
  if (!currentSemester?.holidays) return false;
  const startHoliday = currentSemester.holidays.find(h =>
    h.name.toLowerCase().includes('spring break start')
  );
  const endHoliday = currentSemester.holidays.find(h =>
    h.name.toLowerCase().includes('spring break end')
  );
  if (!startHoliday || !endHoliday) return false;
  return dateStr >= startHoliday.date && dateStr <= endHoliday.date;
}

function isInFinalPeriod(dateStr) {
  if (!currentSemester?.finalPeriodStart || !currentSemester?.finalPeriodEnd) return false;
  return dateStr >= currentSemester.finalPeriodStart && dateStr <= currentSemester.finalPeriodEnd;
}

function isBeforeClasses(dateStr) {
  if (!currentSemester?.startDate) return false;
  return dateStr < currentSemester.startDate;
}

function isAfterClasses(dateStr) {
  if (!currentSemester?.lastClassDate) return false;
  return dateStr > currentSemester.lastClassDate;
}

function getDateLabels(dateStr) {
  if (!currentSemester || !colors) return [];
  const labels = [];
  const dateKeys = Object.keys(colors.dates);
  for (const key of dateKeys) {
    if (currentSemester[key] === dateStr) {
      // Skip firstMonday label
      if (key === 'firstMonday') continue;
      // Filter based on hasFinal toggle
      if (hasFinal) {
        // Show HasFinal dates, hide NoFinal dates
        if (key === 'gradesDueNoFinal') continue;
      } else {
        // Show NoFinal dates, hide HasFinal/final period dates
        if (key === 'lastDueHasFinal' || key === 'gradesDueHasFinal') continue;
        if (key === 'finalPeriodStart' || key === 'finalPeriodEnd') continue;
      }
      labels.push(key);
    }
  }
  // When no final, lastClassDate is also the last due date
  if (!hasFinal && dateStr === currentSemester.lastClassDate) {
    labels.push('lastDueDate');
  }
  return labels;
}

function resolveColor(value) {
  if (!value) return null;
  // If it's a hex color, return as-is
  if (value.startsWith('#')) return value;
  // If it's a palette reference like "eecs-red", resolve it
  if (value.includes('-')) {
    const [palette, color] = value.split('-');
    return colors?.palettes?.[palette]?.[color] || null;
  }
  return null;
}

function getColor(level) {
  const value = colors?.levels?.[level];
  return resolveColor(value);
}

function getDateColor(dateStr) {
  const labels = getDateLabels(dateStr);
  let highestLevel = null;
  for (const label of labels) {
    const level = colors.dates[label];
    if (level === 'High') return getColor('High');
    if (level === 'Medium') highestLevel = 'Medium';
  }
  return highestLevel ? getColor(highestLevel) : null;
}

function getHolidayColor(holiday) {
  if (!colors) return '#ffebee';
  const level = colors.holidays[holiday.name];
  if (level) {
    return getColor(level);
  }
  return resolveColor(colors.holidays.default) || colors.holidays.default;
}

function formatLabel(key) {
  // Special case labels
  if (key === 'startDate') return 'First Day of Class';
  if (key === 'lastClassDate') return 'Last Day of Class';
  if (key === 'Monday Schedule Shift') return 'Follow Monday Schedule';
  // Remove "HasFinal" / "NoFinal" suffixes since toggle makes it clear
  let label = key
    .replace(/HasFinal$/, '')
    .replace(/NoFinal$/, '');
  return label.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase()).trim();
}

const dayIndexMap = { M: 0, T: 1, W: 2, R: 3, F: 4 };

function getActiveEventTypes() {
  return Object.entries(eventDays)
    .filter(([_, days]) => days.size > 0)
    .map(([type, _]) => type);
}

function renderSchedule() {
  if (!currentSemester) {
    console.error('No current semester');
    return;
  }
  console.log('Rendering:', currentSemester.name);

  const tbody = document.getElementById('scheduleBody');
  tbody.innerHTML = '';

  // Determine calendar end date
  let endDate;
  if (hasFinal) {
    // Check if gradesDue is within a week of finals end (Spring) vs much later (Fall)
    const finalEnd = new Date(currentSemester.finalPeriodEnd + 'T00:00:00');
    const gradesDue = new Date(currentSemester.gradesDueHasFinal + 'T00:00:00');
    const daysDiff = (gradesDue - finalEnd) / (1000 * 60 * 60 * 24);
    // If grades due within 7 days, extend calendar to show it; otherwise keep finals end
    endDate = daysDiff <= 7 ? currentSemester.gradesDueHasFinal : currentSemester.finalPeriodEnd;
  } else {
    endDate = currentSemester.gradesDueNoFinal;
  }
  console.log('hasFinal:', hasFinal, 'endDate:', endDate);
  // Find the Monday of the week containing startDate
  const startDateObj = new Date(currentSemester.startDate + 'T00:00:00');
  const dayOfWeek = startDateObj.getDay(); // 0=Sun, 1=Mon, ...
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const firstMonday = new Date(startDateObj);
  firstMonday.setDate(firstMonday.getDate() + mondayOffset);
  const firstMondayStr = firstMonday.toISOString().split('T')[0];
  const weeks = generateWeeks(firstMondayStr, endDate);
  console.log('Generated', weeks.length, 'weeks, endDate:', endDate);
  const activeEventTypes = getActiveEventTypes();

  // Track event counters across weeks
  const eventCounters = {
    lecture: 1,
    lab: 1,
    recitation: 1
  };

  weeks.forEach(week => {
    // Collect day info
    const dayInfo = week.days.map((day, dayIndex) => {
      const holiday = getHoliday(day.dateStr);
      const dateLabels = getDateLabels(day.dateStr);
      const inFinals = isInFinalPeriod(day.dateStr);
      const beforeClasses = isBeforeClasses(day.dateStr);
      const afterClasses = isAfterClasses(day.dateStr);
      const afterEndDate = day.dateStr > endDate;
      let bgColor = null;
      let textColor = null;
      let labels = [];

      if (holiday) {
        bgColor = getHolidayColor(holiday);
        labels.push(holiday.name);
      }

      // Mark final exam period (only if class has a final)
      if (inFinals && hasFinal) {
        labels.push('Finals');
        if (!bgColor) bgColor = '#fff3cd';  // Light yellow for finals
      }

      // Check date labels for High (bg) or Medium (text)
      for (const label of dateLabels) {
        const level = colors?.dates?.[label];
        if (level === 'High') {
          bgColor = getColor('High');
        } else if (level === 'Medium') {
          textColor = getColor('Medium');
        }
        labels.push(formatLabel(label));
      }

      // Only startDate goes in date cell, lastClassDate stays in label row
      const dateRowLabels = dateLabels.filter(l => l === 'startDate');
      const labelRowLabels = labels.filter(l => l !== 'First Day of Class');

      return { day, dayIndex, holiday, inFinals, beforeClasses, afterClasses, afterEndDate, bgColor, textColor, labels: labelRowLabels, dateRowLabels };
    });

    // Check if entire week is Spring Break (has both Start and End)
    const hasSpringBreakStart = dayInfo.some(({ holiday }) =>
      holiday?.name?.toLowerCase().includes('spring break start')
    );
    const hasSpringBreakEnd = dayInfo.some(({ holiday }) =>
      holiday?.name?.toLowerCase().includes('spring break end')
    );
    const isSpringBreakWeek = hasSpringBreakStart && hasSpringBreakEnd;

    // Check for Thanksgiving week (Thu + Fri holidays)
    const thanksgivingDays = dayInfo.filter(({ holiday }) =>
      holiday?.name?.toLowerCase().includes('thanksgiving')
    );
    const isThanksgivingWeek = thanksgivingDays.length >= 2;

    // Check for finals period days
    const finalsDays = dayInfo.map((info, idx) => ({ ...info, idx }))
      .filter(({ inFinals }) => inFinals && hasFinal);
    const hasFinalsInWeek = finalsDays.length > 0;

    // Check if label row would have any content
    const hasLabelContent = isSpringBreakWeek || isThanksgivingWeek || hasFinalsInWeek ||
      dayInfo.some(({ labels, beforeClasses, afterEndDate }) =>
        !beforeClasses && !afterEndDate && labels.length > 0
      );

    // Calculate rows for this week (Spring Break has no date row, just label)
    const rowsPerWeek = isSpringBreakWeek
      ? 1
      : 1 + (hasLabelContent ? 1 : 0) + activeEventTypes.length;

    // Date row (skip for Spring Break)
    if (!isSpringBreakWeek) {
      const dateRow = document.createElement('tr');
      dateRow.className = 'date-row';
      const weekTd = document.createElement('td');
      weekTd.className = 'week-header';
      weekTd.rowSpan = rowsPerWeek;
      weekTd.textContent = week.number;
      dateRow.appendChild(weekTd);
      dayInfo.forEach(({ day, beforeClasses, afterEndDate, dateRowLabels }) => {
        const td = document.createElement('td');
        if (!beforeClasses && !afterEndDate) {
          // Include special labels in date cell
          let dateText = day.display;
          if (dateRowLabels && dateRowLabels.length > 0) {
            const labelText = dateRowLabels.map(l => formatLabel(l)).join(', ');
            dateText = `${day.display} (${labelText})`;
          }
          td.textContent = dateText;
          const dateColor = resolveColor(colors?.date) || colors?.date;
          if (dateColor) {
            td.style.backgroundColor = dateColor;
          }
        }
        dateRow.appendChild(td);
      });
      tbody.appendChild(dateRow);
    }

    // Label row (holidays/milestones) - only if there's content
    if (hasLabelContent) {
      const labelRow = document.createElement('tr');
      labelRow.className = 'label-row';

      if (isSpringBreakWeek) {
        // Add week header for Spring Break row
        const weekTd = document.createElement('td');
        weekTd.className = 'week-header';
        weekTd.rowSpan = 1;
        weekTd.textContent = week.number;
        labelRow.appendChild(weekTd);

        // Get date range from first and last day of week
        const startDate = new Date(dayInfo[0].day.dateStr + 'T00:00:00');
        const endDate = new Date(dayInfo[4].day.dateStr + 'T00:00:00');
        const startStr = startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const endStr = endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        const td = document.createElement('td');
        td.colSpan = 5;
        td.textContent = `Spring Break (${startStr} - ${endStr})`;
        td.style.backgroundColor = getHolidayColor({ name: 'Spring Break' });
        labelRow.appendChild(td);
      } else if (isThanksgivingWeek) {
        // Render Mon-Wed normally, merge Thu-Fri for Thanksgiving
        dayInfo.slice(0, 3).forEach(({ beforeClasses, bgColor, textColor, labels }) => {
          const td = document.createElement('td');
          if (!beforeClasses) {
            if (bgColor) td.style.backgroundColor = bgColor;
            if (textColor) td.style.color = textColor;
            td.innerHTML = labels.join('<br>');
          }
          labelRow.appendChild(td);
        });
        const td = document.createElement('td');
        td.colSpan = 2;
        td.textContent = 'Thanksgiving';
        td.style.backgroundColor = getHolidayColor({ name: 'Thanksgiving Holiday' });
        labelRow.appendChild(td);
      } else if (hasFinalsInWeek) {
        // Render non-finals days normally, merge finals days
        const firstFinalsIdx = finalsDays[0].idx;
        const finalsCount = finalsDays.length;

        // Days before finals
        dayInfo.slice(0, firstFinalsIdx).forEach(({ beforeClasses, afterClasses, bgColor, textColor, labels }) => {
          const td = document.createElement('td');
          if (!beforeClasses && !afterClasses) {
            if (bgColor) td.style.backgroundColor = bgColor;
            if (textColor) td.style.color = textColor;
            td.innerHTML = labels.join('<br>');
          }
          labelRow.appendChild(td);
        });

        // Merged finals cell
        const td = document.createElement('td');
        td.colSpan = finalsCount;

        // Only show grades due in finals cell for Fall (when it's >7 days after finals end)
        const gradesDueDate = currentSemester.gradesDueHasFinal;
        const finalEnd = new Date(currentSemester.finalPeriodEnd + 'T00:00:00');
        const gradesDue = new Date(gradesDueDate + 'T00:00:00');
        const daysDiff = (gradesDue - finalEnd) / (1000 * 60 * 60 * 24);

        if (daysDiff > 7) {
          // Fall term - grades due is next year
          const gradesDueFormatted = gradesDue.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
          td.innerHTML = `Finals Period<br><small>Grades Due: ${gradesDueFormatted}</small>`;
        } else {
          td.textContent = 'Finals Period';
        }
        td.style.backgroundColor = '#fff3cd';
        labelRow.appendChild(td);

        // Days after finals (if any in same week)
        dayInfo.slice(firstFinalsIdx + finalsCount).forEach(({ beforeClasses, bgColor, textColor, labels }) => {
          const td = document.createElement('td');
          if (!beforeClasses) {
            if (bgColor) td.style.backgroundColor = bgColor;
            if (textColor) td.style.color = textColor;
            td.innerHTML = labels.join('<br>');
          }
          labelRow.appendChild(td);
        });
      } else {
        dayInfo.forEach(({ beforeClasses, afterEndDate, bgColor, textColor, labels }) => {
          const td = document.createElement('td');
          if (!beforeClasses && !afterEndDate) {
            if (bgColor) td.style.backgroundColor = bgColor;
            if (textColor) td.style.color = textColor;
            td.innerHTML = labels.join('<br>');
          }
          labelRow.appendChild(td);
        });
      }
      tbody.appendChild(labelRow);
    }

    // Event rows
    activeEventTypes.forEach(eventType => {
      const eventRow = document.createElement('tr');
      eventRow.className = 'event-row';
      const selectedDays = eventDays[eventType];

      dayInfo.forEach(({ dayIndex, holiday, beforeClasses, afterClasses, afterEndDate }) => {
        const td = document.createElement('td');
        let effectiveDayKey = Object.keys(dayIndexMap).find(k => dayIndexMap[k] === dayIndex);

        // Monday Schedule Shift: treat this day as Monday
        if (holiday?.name === 'Monday Schedule Shift') {
          effectiveDayKey = 'M';
        }

        // No events before or after class period, or after calendar end
        if (beforeClasses || afterClasses || afterEndDate) {
          eventRow.appendChild(td);
          return;
        }

        if (selectedDays.has(effectiveDayKey)) {
          const inSpringBreak = isInSpringBreak(dayInfo[dayIndex].day.dateStr);
          if ((holiday && holiday.name !== 'Monday Schedule Shift') || inSpringBreak) {
            // Holiday or Spring Break - no class (but Monday Shift still has class)
            td.textContent = '';
          } else {
            // Show numbered event
            const label = eventType.charAt(0).toUpperCase() + eventType.slice(1);
            td.textContent = `${label} ${eventCounters[eventType]}`;
            eventCounters[eventType]++;
            // Apply event color
            const eventColor = resolveColor(colors?.events?.[eventType]) || colors?.events?.[eventType];
            if (eventColor) {
              td.style.backgroundColor = eventColor;
            }
          }
        }
        eventRow.appendChild(td);
      });
      tbody.appendChild(eventRow);
    });

  });
}
