// Data is loaded from data/data.js (RUNS_DATA, PBS_DATA).
// Use add_new_event.py to add or edit events — do not edit data.js manually.

const RUNS           = typeof RUNS_DATA       !== "undefined" ? RUNS_DATA       : [];
const PERSONAL_BESTS = typeof PBS_DATA        !== "undefined" ? PBS_DATA        : [];
const ACTIVITIES     = typeof ACTIVITIES_DATA !== "undefined" ? ACTIVITIES_DATA : [];

// ── i18n ─────────────────────────────────────────────────────

const I18N = {
  en: {
    logo:           "Sergey's <em>Running</em> Log",
    nav_overview:   "Overview",
    nav_runs:       "All Runs",
    nav_pbs:        "Personal Bests",
    ov_since:       function(y) { return 'Since ' + y + ' · Georgia'; },
    ov_headline:    function(km, n) { return '<span style="color:var(--accent)">' + km + '&nbsp;km</span> raced across ' + n + ' finish lines.'; },
    ov_climbed:     "Climbed",
    ov_longest:     "Longest race",
    ov_fastest5k:   "Fastest 5K",
    ov_explore:     "Explore the log →",
    ov_memories:    "Race memories",
    ov_meta:        function(p, m) { return p + ' photos · ' + m + ' medals'; },
    ov_more_photos: "photos",
    ov_latest:      "Latest race",
    ov_new_pb:      function(d) { return 'NEW ' + d + ' PB'; },
    pbp_label:      function(n) { return n >= 2 ? n + ' years, chipping away' : 'Chipping away'; },
    pace:           "Pace",
    avg_hr:         "Avg HR",
    max_hr:         "Max HR",
    sneakers:       "Sneakers",
    video:          "Video",
    min_km:         "min/km",
    bpm:            "bpm",
    avg:            "avg",
    max:            "max",
    km:             "km",
    total_time:     "Total time",
    elevation:      "Elevation",
    m:              "m",
    pbc_distance:    "Distance",
    pbc_pace:        "Pace",
    pbc_time:        "Time",
    filter_year:     "Year",
    filter_distance: "Distance",
    filter_search:   "Location",
    filter_search_ph: "e.g. Batumi or Georgia",
    filter_race:     "Race",
    filter_race_ph:  "Kazbegi",
    filter_reset:    "Reset",
    all_years:       "All years",
    all_distances:   "All distances",
    dist_lt5:        "< 5 km",
    dist_5_10:       "5 – 9.99 km",
    dist_10_42:      "10 – 42 km",
    dist_gt42:       "> 42 km",
    dist_custom:     "Custom",
    filter_trail:    "Trail",
    trail_all:       "All",
    trail_yes:       "Trail",
    trail_no:        "Non-trail",
    runs_shown:     function(n, t) { return n + ' / ' + t + ' runs'; },
    photos_details: "Photos & details",
    hide_details:   "Hide details",
    det_date:       "Date",
    det_location:   "Location",
    det_distance:   "Distance",
    det_pace:       "Pace",
    det_avg_hr:     "Avg HR",
    det_max_hr:     "Max HR",
    det_sneakers:   "Sneakers",
    det_video:      "Video",
    tag_sprint:     "Sprint",
    tag_mid:        "Middle distance",
    tag_long:       "Long distance",
    tag_marathon:   "Marathon",
    tag_ultra:      "Ultramarathon",
    tag_trail:      "Trail",
    photos:         "Photos",
    no_photos:      "No photos added yet.",
    date_place:     "Date & Place",
    heart_rate:     "Heart Rate",
    prev_records:   "Previous Records",
    first_time:     "This is your first recorded time for this distance.",
    locale:              "en-GB",
    nav_activities:      "Activities",
    act_type_lbl:        "Activity",
    act_metric_lbl:      "Show",
    act_period_lbl:      "Period",
    act_all_running:     "All running",
    act_metric_dist:     "Distance",
    act_metric_runs:     "Runs",
    act_metric_time:     "Time",
    act_period_week:     "Last 7 days",
    act_period_curr_month: "This month",
    act_period_last_month: "Last month",
    act_period_curr_year:  "This year",
    act_period_last_year:  "Last year",
    act_period_custom:   "Custom",
    act_period_all:      "All years",
    act_search_ph:       "Search by type or date…",
    act_no_data:         "No activities in selected period",
    act_h:               "h",
    act_min:             "min",
    act_period_duration: "Period",
    act_avg_week:        "avg km/week",
    act_avg_month:       "avg km/month",
    act_avg_year:        "avg km/year",
    act_yr:              "yr",
    act_mo:              "mo",
    act_d:               "d",
    cmp_lbl:             "Comparison",
    cmp_period_lbl:      "Period",
    cmp_week:            "Week vs week",
    cmp_month:           "Month vs month",
    cmp_year:            "Year vs year",
    cmp_custom:          "Custom",
    cmp_p1:              "Period 1",
    cmp_p2:              "Period 2",
  },
  be: {
    logo:           "<em>Бегавы</em> дзённік Сяргея",
    nav_overview:   "Агляд",
    nav_runs:       "Усе забегі",
    nav_pbs:        "Асабістыя рэкорды",
    ov_since:       function(y) { return 'З ' + y + ' · Грузія'; },
    ov_headline:    function(km, n) { return '<span style="color:var(--accent)">' + km + '&nbsp;км</span> на ' + n + ' фінішах.'; },
    ov_climbed:     "Набор вышыні",
    ov_longest:     "Самая доўгая",
    ov_fastest5k:   "Хуткі 5К",
    ov_explore:     "Адкрыць журнал →",
    ov_memories:    "Успаміны з гонак",
    ov_meta:        function(p, m) { return p + ' фота · ' + m + ' медалёў'; },
    ov_more_photos: "фота",
    ov_latest:      "Апошняя гонка",
    ov_new_pb:      function(d) { return 'НОВЫ РЭКОРД ' + d; },
    pbp_label:      function(n) { if (n < 2) return 'Прагрэс'; var w = (n >= 2 && n <= 4) ? 'гады' : 'гадоў'; return n + ' ' + w + ' прагрэсу'; },
    pace:           "Тэмп",
    avg_hr:         "Сяр. пульс",
    max_hr:         "Макс. пульс",
    sneakers:       "Красоўкі",
    video:          "Відэа",
    min_km:         "хв/км",
    bpm:            "уд/хв",
    avg:            "сяр.",
    max:            "макс.",
    km:             "км",
    total_time:     "Агульны час",
    elevation:      "Набор",
    m:              "м",
    pbc_distance:    "Адлегласць",
    pbc_pace:        "Тэмп",
    pbc_time:        "Час",
    filter_year:     "Год",
    filter_distance: "Адлегласць",
    filter_search:   "Месца",
    filter_search_ph: "напр. Батумі або Грузія",
    filter_race:     "Забег",
    filter_race_ph:  "Kazbegi",
    filter_reset:    "Скінуць",
    all_years:       "Усе гады",
    all_distances:   "Усе адлегласці",
    dist_lt5:        "< 5 км",
    dist_5_10:       "5 – 9.99 км",
    dist_10_42:      "10 – 42 км",
    dist_gt42:       "> 42 км",
    dist_custom:     "Адвольная",
    filter_trail:    "Трэйл",
    trail_all:       "Усе",
    trail_yes:       "Трэйл",
    trail_no:        "Не трэйл",
    runs_shown:     function(n, t) { return n + ' / ' + t + ' забегаў'; },
    photos_details: "Фота і падрабязнасці",
    hide_details:   "Схаваць падрабязнасці",
    det_date:       "Дата",
    det_location:   "Месца",
    det_distance:   "Адлегласць",
    det_pace:       "Тэмп",
    det_avg_hr:     "Сяр. пульс",
    det_max_hr:     "Макс. пульс",
    det_sneakers:   "Красоўкі",
    det_video:      "Відэа",
    tag_sprint:     "Спрынт",
    tag_mid:        "Сярэдняя дыстанцыя",
    tag_long:       "Доўгая дыстанцыя",
    tag_marathon:   "Марафон",
    tag_ultra:      "Ультрамарафон",
    tag_trail:      "Трэйл",
    photos:         "Фота",
    no_photos:      "Фота пакуль не дададзены.",
    date_place:     "Дата і месца",
    heart_rate:     "Пульс",
    prev_records:   "Папярэднія рэкорды",
    first_time:     "Гэта ваш першы запісаны вынік на гэтай дыстанцыі.",
    locale:              "be",
    nav_activities:      "Актыўнасці",
    act_type_lbl:        "Актыўнасць",
    act_metric_lbl:      "Паказаць",
    act_period_lbl:      "Перыяд",
    act_all_running:     "Увесь бег",
    act_metric_dist:     "Адлегласць",
    act_metric_runs:     "Забегі",
    act_metric_time:     "Час",
    act_period_week:     "Апошнія 7 дзён",
    act_period_curr_month: "Гэты месяц",
    act_period_last_month: "Мінулы месяц",
    act_period_curr_year:  "Гэты год",
    act_period_last_year:  "Мінулы год",
    act_period_custom:   "Адвольны",
    act_period_all:      "Усе гады",
    act_search_ph:       "Пошук па тыпе або даце…",
    act_no_data:         "Няма актыўнасці за абраны перыяд",
    act_h:               "г",
    act_min:             "хв",
    act_period_duration: "Перыяд",
    act_avg_week:        "сяр. км/тыдзень",
    act_avg_month:       "сяр. км/месяц",
    act_avg_year:        "сяр. км/год",
    act_yr:              "г",
    act_mo:              "м",
    act_d:               "д",
    cmp_lbl:             "Параўнанне",
    cmp_period_lbl:      "Перыяд",
    cmp_week:            "Тыдзень vs тыдзень",
    cmp_month:           "Месяц vs месяц",
    cmp_year:            "Год vs год",
    cmp_custom:          "Адвольны",
    cmp_p1:              "Перыяд 1",
    cmp_p2:              "Перыяд 2",
  },
};

let LANG = localStorage.getItem('lang') || 'be';
const t = key => I18N[LANG][key];

// ── Security: escape untrusted data before it enters innerHTML ──
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
// Only allow http(s) links; anything else (javascript:, data:, …) is neutralised.
function safeUrl(u) {
  var s = String(u || '').trim();
  return /^https?:\/\//i.test(s) ? s : '';
}

function locStr(obj) {
  return (LANG === 'be' && obj.location_be) ? obj.location_be : obj.location;
}

function searchStr(obj) {
  return (locStr(obj) + ' ' + (obj.country || '') + ' ' + (obj.country_be || '')).toLowerCase();
}

function pbDistLabel(pb) {
  var m = /^\s*([\d.,]+)\s*(km|км|m|м)\s*$/i.exec(pb.distance || '');
  if (!m) return pb.distance;
  var isMeters = /^(m|м)$/i.test(m[2]);
  return m[1] + ' ' + (isMeters ? t('m') : t('km'));
}

// ── Helpers ───────────────────────────────────────────────────

var BE_MONTHS = [
  'студзеня','лютага','сакавіка','красавіка','траўня','чэрвеня',
  'ліпеня','жніўня','верасня','кастрычніка','лістапада','снежня'
];

var BE_MONTHS_SHORT = [
  'студз','лют','сак','крас','трав','чэрв',
  'ліп','жн','вер','кастр','ліст','снеж'
];

function fmtDate(str) {
  var d = new Date(str + 'T12:00:00');
  if (LANG === 'be') {
    return d.getDate() + ' ' + BE_MONTHS[d.getMonth()] + ' ' + d.getFullYear();
  }
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

function calcPace(distance_km, total_time) {
  var parts = total_time.split(':').map(Number);
  var totalSec = parts.length === 3
    ? parts[0] * 3600 + parts[1] * 60 + parts[2]
    : parts[0] * 60 + parts[1];
  var paceSecPerKm = totalSec / distance_km;
  var pm = Math.floor(paceSecPerKm / 60);
  var ps = Math.round(paceSecPerKm % 60);
  if (ps === 60) { pm++; ps = 0; }
  return pm + ':' + (ps < 10 ? '0' + ps : ps);
}

function photoGrid(photos) {
  if (!photos || photos.length === 0)
    return '<p class="no-photos">' + t('no_photos') + '</p>';
  var id = 'pg' + (photoGrid._id = (photoGrid._id || 0) + 1);
  // store the array globally so the lightbox can navigate it
  photoGrid._sets = photoGrid._sets || {};
  photoGrid._sets[id] = photos;
  return '<div class="photos-grid" data-pgid="' + id + '">' +
    photos.map(function(src, i) {
      return '<div class="photo-thumb" data-action="open-lb" data-set="' + id + '" data-idx="' + i + '">' +
               '<img src="' + esc(src) + '" alt="" loading="lazy">' +
             '</div>';
    }).join('') +
  '</div>';
}

// ── PB Chart ──────────────────────────────────────────────────

var pbChartMetric = 'pace';

var pbChartExpanded = true;

function togglePBChart() {
  pbChartExpanded = !pbChartExpanded;
  document.getElementById('pbc-svg').style.display    = pbChartExpanded ? '' : 'none';
  document.getElementById('pbc-toggle').textContent   = pbChartExpanded ? '▾' : '▸';
}

function setPBChartMetric(m) {
  pbChartMetric = m;
  document.getElementById('pbc-pace').classList.toggle('active', m === 'pace');
  document.getElementById('pbc-time').classList.toggle('active', m === 'time');
  renderPBChart();
}

function buildPBChartOptions() {
  document.getElementById('pbc-label-dist').textContent = t('pbc_distance');
  document.getElementById('pbc-pace').textContent       = t('pbc_pace');
  document.getElementById('pbc-time').textContent       = t('pbc_time');

  var sel    = document.getElementById('pbc-distance');
  var curVal = sel.value;
  sel.innerHTML = PERSONAL_BESTS.slice().sort(function(a, b) { return a.distance_km - b.distance_km; }).map(function(pb) {
    return '<option value="' + pb.distance + '">' + pbDistLabel(pb) + '</option>';
  }).join('');
  if (curVal && PERSONAL_BESTS.some(function(pb) { return pb.distance === curVal; }))
    sel.value = curVal;
}

function timeToSec(str) {
  var p = str.split(':').map(Number);
  return p.length === 3 ? p[0]*3600 + p[1]*60 + p[2] : p[0]*60 + p[1];
}

function fmtSec(sec) {
  sec = Math.round(sec);
  var h = Math.floor(sec / 3600);
  var m = Math.floor((sec % 3600) / 60);
  var s = sec % 60;
  if (h > 0) return h + ':' + (m < 10 ? '0'+m : m) + ':' + (s < 10 ? '0'+s : s);
  return m + ':' + (s < 10 ? '0'+s : s);
}

function renderPBChart() {
  var svg = document.getElementById('pbc-svg');
  var distName = document.getElementById('pbc-distance').value;
  var pb = PERSONAL_BESTS.find(function(p) { return p.distance === distName; });
  if (!pb) { svg.innerHTML = ''; return; }

  // Collect all data points: previous records + current PB
  var points = (pb.previous_records || []).map(function(r) {
    return { date: r.date, sec: timeToSec(r.time), loc: r.location };
  });
  points.push({ date: pb.date, sec: timeToSec(pb.total_time), loc: pb.location, isBest: true });
  points.sort(function(a, b) { return new Date(a.date) - new Date(b.date); });

  if (points.length < 2) {
    // single point — still draw it
    if (points.length === 0) { svg.innerHTML = ''; return; }
  }

  var W = 760, H = 180, ML = 52, MR = 16, MT = 14, MB = 42;
  var cW = W - ML - MR, cH = H - MT - MB;
  var n  = points.length;
  var isPace = pbChartMetric === 'pace';

  function val(pt) {
    return isPace ? pt.sec / pb.distance_km : pt.sec;
  }

  var vals = points.map(val);
  var minV = Math.min.apply(null, vals), maxV = Math.max.apply(null, vals);
  var pad  = (maxV - minV) * 0.18 || (isPace ? 10 : 30);
  minV = Math.max(0, minV - pad); maxV += pad;
  var range = maxV - minV || 1;

  function xPos(i) { return n === 1 ? ML + cW/2 : ML + (i / (n-1)) * cW; }
  // lower = better → invert: lower value → top of chart
  function yPos(v) { return MT + ((v - minV) / range) * cH; }

  function fmtVal(v) { return fmtSec(v); }

  // y-axis ticks
  var tickCount = 4, yHtml = '';
  for (var ti = 0; ti <= tickCount; ti++) {
    var tv = minV + (ti / tickCount) * range;
    var ty = yPos(tv);
    yHtml +=
      '<line x1="' + ML + '" y1="' + ty + '" x2="' + (ML+cW) + '" y2="' + ty +
        '" stroke="var(--border)" stroke-width="1"/>' +
      '<text x="' + (ML-5) + '" y="' + (ty+4) +
        '" text-anchor="end" font-size="10" font-family="inherit" fill="var(--muted)">' +
        fmtVal(tv) + '</text>';
  }

  // x-axis: label every point with short date
  var xHtml = points.map(function(pt, i) {
    var d    = new Date(pt.date + 'T12:00:00');
    var mon  = LANG === 'be'
      ? BE_MONTHS_SHORT[d.getMonth()]
      : d.toLocaleDateString('en-GB', { month: 'short' });
    var line1 = mon + ' ' + d.getDate();
    var line2 = d.getFullYear();
    var x = xPos(i);
    return '<text x="' + x + '" y="' + (MT+cH+16) +
      '" text-anchor="middle" font-size="10" font-family="inherit" fill="var(--muted)">' + line1 + '</text>' +
      '<text x="' + x + '" y="' + (MT+cH+28) +
      '" text-anchor="middle" font-size="10" font-family="inherit" fill="var(--muted)">' + line2 + '</text>';
  }).join('');

  // trend line
  var lineHtml = n > 1
    ? '<polyline points="' + points.map(function(pt,i){return xPos(i)+','+yPos(val(pt));}).join(' ') +
      '" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" opacity="0.7"/>'
    : '';

  // dots — current PB gets a larger filled circle
  var dotsHtml = points.map(function(pt, i) {
    var v   = val(pt);
    var tip = fmtDate(pt.date) + ' · ' + pt.loc + '\n' + fmtVal(v) + (isPace ? ' ' + t('min_km') : '');
    var r   = pt.isBest ? 7 : 5;
    var fill = pt.isBest ? 'var(--accent)' : 'var(--card)';
    var stroke = 'var(--accent)';
    var sw = pt.isBest ? 0 : 2.5;
    return '<circle cx="' + xPos(i) + '" cy="' + yPos(v) + '" r="' + r + '"' +
      ' fill="' + fill + '" stroke="' + stroke + '" stroke-width="' + sw + '">' +
      '<title>' + tip.replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</title></circle>';
  }).join('');

  svg.innerHTML = yHtml + xHtml + lineHtml + dotsHtml;
}

// ── Filters ───────────────────────────────────────────────────

var DIST_RANGES = [
  { key: 'lt5',   label: 'dist_lt5',   test: function(d) { return d < 5; } },
  { key: '5_10',  label: 'dist_5_10',  test: function(d) { return d >= 5 && d < 10; } },
  { key: '10_42', label: 'dist_10_42', test: function(d) { return d >= 10 && d <= 42; } },
  { key: 'gt42',  label: 'dist_gt42',  test: function(d) { return d > 42; } },
];

function distRangeTest(run, rangeKey) {
  var r = DIST_RANGES.find(function(r) { return r.key === rangeKey; });
  return r ? r.test(run.distance_km) : true;
}

function buildDistOptions(pool, dSel, keepVal) {
  var usedRanges = DIST_RANGES.filter(function(r) {
    return pool.some(function(run) { return r.test(run.distance_km); });
  });
  dSel.innerHTML = '<option value="">' + t('all_distances') + '</option>' +
    usedRanges.map(function(r) { return '<option value="' + r.key + '">' + t(r.label) + '</option>'; }).join('') +
    '<option value="custom">' + t('dist_custom') + '</option>';
  if (keepVal && (keepVal === 'custom' || usedRanges.some(function(r) { return r.key === keepVal; }))) dSel.value = keepVal;
  var customInput = document.getElementById('filter-dist-custom');
  if (customInput) customInput.style.display = (dSel.value === 'custom') ? '' : 'none';
}

function buildFilterOptions() {
  // Static labels & placeholders only; option lists are built by rebuildFacets().
  document.getElementById('flabel-year').textContent     = t('filter_year');
  document.getElementById('flabel-distance').textContent = t('filter_distance');
  document.getElementById('flabel-search').textContent   = t('filter_search');
  document.getElementById('filter-search').placeholder   = t('filter_search_ph');
  document.getElementById('flabel-race').textContent     = t('filter_race');
  document.getElementById('filter-race').placeholder     = t('filter_race_ph');
  document.getElementById('flabel-trail').textContent    = t('filter_trail');
  document.getElementById('filter-reset').textContent    = t('filter_reset');
}

function currentFilters() {
  var search = document.getElementById('filter-search').value.trim().toLowerCase();
  if (search.length < 3) search = '';
  var race = document.getElementById('filter-race').value.trim().toLowerCase();
  if (race.length < 3) race = '';
  return {
    year:      document.getElementById('filter-year').value,
    distance:  document.getElementById('filter-distance').value,
    customVal: parseFloat(document.getElementById('filter-dist-custom').value),
    search:    search,
    race:      race,
    trail:     document.getElementById('filter-trail').value,
  };
}

// True if run r passes every active filter except `exclude` (used for faceting).
function runPasses(r, f, exclude) {
  if (exclude !== 'year'     && f.year && r.date.slice(0, 4) !== f.year) return false;
  if (exclude !== 'distance' && f.distance) {
    if (f.distance === 'custom') {
      if (isNaN(f.customVal) || Math.abs(r.distance_km - f.customVal) > 0.05) return false;
    } else if (!distRangeTest(r, f.distance)) return false;
  }
  if (exclude !== 'search' && f.search && !searchStr(r).includes(f.search)) return false;
  if (exclude !== 'race'   && f.race   && (r.race_name || '').toLowerCase().indexOf(f.race) === -1) return false;
  if (exclude !== 'trail'  && f.trail) {
    if (f.trail === 'yes' && !(r.elevation > 0)) return false;
    if (f.trail === 'no'  &&   r.elevation > 0)  return false;
  }
  return true;
}

// Each dropdown shows only options valid given the OTHER active filters.
function rebuildFacets(f) {
  // Year — runs matching all filters except Year
  var ySel  = document.getElementById('filter-year');
  var yPool = RUNS.filter(function(r) { return runPasses(r, f, 'year'); });
  var years = [...new Set(yPool.map(function(r) { return r.date.slice(0, 4); }))];
  if (f.year && years.indexOf(f.year) === -1) years.push(f.year);
  years.sort().reverse();
  ySel.innerHTML = '<option value="">' + t('all_years') + '</option>' +
    years.map(function(y) { return '<option value="' + y + '">' + y + '</option>'; }).join('');
  ySel.value = f.year;

  // Distance — runs matching all filters except Distance (Custom always added)
  var dSel  = document.getElementById('filter-distance');
  var dPool = RUNS.filter(function(r) { return runPasses(r, f, 'distance'); });
  buildDistOptions(dPool, dSel, f.distance);

  // Trail — runs matching all filters except Trail
  var trSel  = document.getElementById('filter-trail');
  var trPool = RUNS.filter(function(r) { return runPasses(r, f, 'trail'); });
  var hasYes = trPool.some(function(r) { return r.elevation > 0; });
  var hasNo  = trPool.some(function(r) { return !(r.elevation > 0); });
  trSel.innerHTML = '<option value="">' + t('trail_all') + '</option>' +
    (hasYes || f.trail === 'yes' ? '<option value="yes">' + t('trail_yes') + '</option>' : '') +
    (hasNo  || f.trail === 'no'  ? '<option value="no">'  + t('trail_no')  + '</option>' : '');
  trSel.value = f.trail;
}

var _searchTimer;
function onSearchInput() {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(function() {
    var v = document.getElementById('filter-search').value.trim();
    if (v.length === 0 || v.length >= 3) applyFilters('search');
  }, 300);
}

var _raceTimer;
function onRaceInput() {
  clearTimeout(_raceTimer);
  _raceTimer = setTimeout(function() {
    var v = document.getElementById('filter-race').value.trim();
    if (v.length === 0 || v.length >= 3) applyFilters('race');
  }, 300);
}

function applyFilters() {
  // Toggle the custom-distance input
  var customInput = document.getElementById('filter-dist-custom');
  var isCustom = document.getElementById('filter-distance').value === 'custom';
  customInput.style.display = isCustom ? '' : 'none';
  if (!isCustom) customInput.value = '';

  var f = currentFilters();
  rebuildFacets(f);                         // narrow each dropdown to valid options

  var filtered = RUNS.filter(function(r) { return runPasses(r, f, null); });

  renderRuns(filtered, f.search, f.race);
  document.getElementById('runs-count-bar').textContent =
    (filtered.length < RUNS.length) ? t('runs_shown')(filtered.length, RUNS.length) : '';
}

function resetFilters() {
  document.getElementById('filter-year').value     = '';
  document.getElementById('filter-distance').value = '';
  document.getElementById('filter-dist-custom').value  = '';
  document.getElementById('filter-dist-custom').style.display = 'none';
  document.getElementById('filter-search').value   = '';
  document.getElementById('filter-race').value     = '';
  document.getElementById('filter-trail').value    = '';
  applyFilters();
}

// ── Render: All Runs ──────────────────────────────────────────

var DTYPE_DEFS = [
  { key: 'sprint',   emoji: '⚡', tag: 'tag_sprint',   test: function(m) { return m <= 400; } },
  { key: 'mid',      emoji: '🏃', tag: 'tag_mid',      test: function(m) { return m <= 3000; } },
  { key: 'long',     emoji: '🏅', tag: 'tag_long',     test: function(m) { return m < 42195; } },
  { key: 'marathon', emoji: '🎽', tag: 'tag_marathon',  test: function(m) { return m === 42195; } },
  { key: 'ultra',    emoji: '🏔', tag: 'tag_ultra',    test: function(m) { return true; } },
];

function getDistanceType(run) {
  var m = Math.round(run.distance_km * 1000);
  for (var i = 0; i < DTYPE_DEFS.length; i++) {
    if (DTYPE_DEFS[i].test(m)) return DTYPE_DEFS[i];
  }
}

function runTags(run) {
  var dt   = getDistanceType(run);
  var tags = ['<span class="run-tag run-tag-' + dt.key + '"><span class="run-tag-emoji">' + dt.emoji + '</span>' + t(dt.tag) + '</span>'];
  if ((run.elevation || 0) > 0)
    tags.push('<span class="run-tag run-tag-trail"><span class="run-tag-emoji">🌿</span>' + t('tag_trail') + '</span>');
  return '<div class="run-tags">' + tags.join('') + '</div>';
}

function hlText(text, query) {
  var safe = esc(text);                       // escape first — output is safe HTML
  if (!query) return safe;
  var re = new RegExp('(' + esc(query).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
  return safe.replace(re, '<mark>$1</mark>');
}

function renderRuns(runs, searchQuery, raceQuery) {
  if (!runs) runs = RUNS;
  var sorted = runs.slice().sort(function(a, b) {
    return new Date(b.date) - new Date(a.date);
  });

  photoGrid._sets = photoGrid._sets || {};

  document.getElementById('page-runs').innerHTML = sorted.map(function(run, i) {
    var photos = run.photos || [];
    var lbSet  = photos.length ? photos : (run.medal ? [run.medal] : []);
    var setId  = 'run' + i;
    photoGrid._sets[setId] = lbSet;

    // Photo strip: first 3 run photos; pad with the medal, then cycle if fewer
    var stripHtml = '';
    if (photos.length > 0) {
      var strip = photos.slice(0, 3);
      if (strip.length < 3 && run.medal) strip.push(run.medal);
      var base = strip.slice();
      while (strip.length < 3) strip.push(base[strip.length % base.length]);
      stripHtml = '<div class="rc-strip">' +
        strip.map(function(src, n) {
          var idx = Math.min(n, lbSet.length - 1);
          return '<img src="' + esc(src) + '" alt="" loading="lazy" data-action="open-lb" data-set="' + setId + '" data-idx="' + idx + '">';
        }).join('') +
        (run.medal ? '<img class="rc-medal" src="' + esc(run.medal) + '" alt="medal" loading="lazy" data-action="open-lb-single">' : '') +
      '</div>';
    } else if (run.medal) {
      stripHtml = '<div class="rc-strip single">' +
        '<img src="' + esc(run.medal) + '" alt="medal" loading="lazy" data-action="open-lb-single">' +
      '</div>';
    }

    var title = run.race_name
      ? hlText(run.race_name, raceQuery)
      : hlText(locStr(run), searchQuery);
    var elev = run.elevation || 0;

    return '<article class="run-card">' +
      stripHtml +
      '<div class="rc-body">' +
        '<div class="rc-meta">' + fmtDate(run.date) + ' · ' + hlText(locStr(run), searchQuery) + '</div>' +
        '<div class="rc-titlerow">' +
          '<div class="rc-title">' + title + '</div>' +
          '<div class="rc-dist">' + esc(run.distance_km) + '<small> ' + t('km') + '</small></div>' +
        '</div>' +
        runTags(run) +
      '</div>' +
      '<div class="run-stats">' +
        '<div class="stat"><div class="stat-label">' + t('pace') + '</div><div class="stat-value">' + esc(calcPace(run.distance_km, run.total_time)) + '</div><div class="stat-sub">' + t('min_km') + '</div></div>' +
        '<div class="stat"><div class="stat-label">' + t('elevation') + '</div><div class="stat-value">' + (elev > 0 ? esc(elev) : '—') + '</div><div class="stat-sub">' + (elev > 0 ? t('m') : '') + '</div></div>' +
        '<div class="stat"><div class="stat-label">' + t('avg_hr') + '</div><div class="stat-value">' + esc(run.hr_avg || '--') + '</div><div class="stat-sub">' + (run.hr_avg ? t('bpm') : '') + '</div></div>' +
        '<div class="stat"><div class="stat-label">' + t('total_time') + '</div><div class="stat-value">' + esc(run.total_time) + '</div></div>' +
      '</div>' +
    '</article>';
  }).join('');
}

// ── Render: Overview ──────────────────────────────────────────

function renderOverview() {
  var el = document.getElementById('page-overview');
  if (!el) return;
  if (RUNS.length === 0) { el.innerHTML = ''; return; }

  var totalKm   = RUNS.reduce(function(s, r) { return s + r.distance_km; }, 0);
  var climbed   = RUNS.reduce(function(s, r) { return s + (r.elevation || 0); }, 0);
  var longest   = Math.max.apply(null, RUNS.map(function(r) { return r.distance_km; }));
  var firstYear = Math.min.apply(null, RUNS.map(function(r) { return +r.date.slice(0, 4); }));
  var sorted    = RUNS.slice().sort(function(a, b) { return b.date.localeCompare(a.date); });
  var latest    = sorted[0];
  var pb5       = PERSONAL_BESTS.find(function(p) { return p.distance_km === 5; });

  // Hero photo: the photo-rich run with the most elevation (mountains first)
  var withPhotos = sorted.filter(function(r) { return r.photos && r.photos.length; });
  var heroRun = withPhotos.slice().sort(function(a, b) { return (b.elevation || 0) - (a.elevation || 0); })[0];
  var heroSrc = heroRun ? heroRun.photos[0] : '';

  // All photos (newest first) back the memories lightbox
  var allPhotos = [];
  withPhotos.forEach(function(r) { allPhotos = allPhotos.concat(r.photos); });
  photoGrid._sets = photoGrid._sets || {};
  photoGrid._sets['ov'] = allPhotos;

  var gridRuns = withPhotos.slice(0, 4);
  var medals   = RUNS.filter(function(r) { return r.medal; }).length;

  var cells = gridRuns.map(function(r, i) {
    var idx = allPhotos.indexOf(r.photos[0]);
    var cap = (i === 0 || i === 2)
      ? '<div class="ov-cap">' + esc(r.race_name || locStr(r)) + ' · ' + esc(r.distance_km) + ' ' + t('km') + '</div>'
      : '';
    return '<div class="ov-cell' + (i === 0 ? ' big' : '') + '" data-action="open-lb" data-set="ov" data-idx="' + idx + '">' +
      '<img src="' + esc(r.photos[0]) + '" alt="" loading="lazy">' + cap + '</div>';
  });
  var extra = Math.max(0, allPhotos.length - gridRuns.length);
  cells.push('<div class="ov-cell ov-more" data-action="open-lb" data-set="ov" data-idx="' + Math.min(4, Math.max(allPhotos.length - 1, 0)) + '">+ ' + extra + '<small>' + t('ov_more_photos') + '</small></div>');

  var newPb = PERSONAL_BESTS.find(function(p) { return p.date === latest.date; });

  el.innerHTML =
    '<div class="ov-hero">' +
      (heroSrc ? '<img class="ov-hero-img" src="' + esc(heroSrc) + '" alt="">' : '') +
      '<div class="ov-hero-grad"></div>' +
      '<div class="ov-hero-inner">' +
        '<div class="ov-eyebrow">' + t('ov_since')(firstYear) + '</div>' +
        '<div class="ov-headline">' + t('ov_headline')(Math.round(totalKm), RUNS.length) + '</div>' +
        '<div class="ov-statrow">' +
          '<div><div class="ov-stat-num">' + climbed.toLocaleString() + '<small> ' + t('m') + '</small></div><div class="ov-stat-lbl">' + t('ov_climbed') + '</div></div>' +
          '<div><div class="ov-stat-num">' + esc(longest) + '<small> ' + t('km') + '</small></div><div class="ov-stat-lbl">' + t('ov_longest') + '</div></div>' +
          (pb5 ? '<div><div class="ov-stat-num">' + esc(pb5.total_time.replace(/^0:/, '')) + '</div><div class="ov-stat-lbl">' + t('ov_fastest5k') + '</div></div>' : '') +
          '<button class="ov-explore" data-action="show-runs">' + t('ov_explore') + '</button>' +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="ov-col ov-mem">' +
      '<div class="ov-mem-head">' +
        '<div class="ov-mem-title">' + t('ov_memories') + '</div>' +
        '<div class="ov-mem-meta">' + t('ov_meta')(allPhotos.length, medals) + '</div>' +
      '</div>' +
      '<div class="ov-grid">' + cells.join('') + '</div>' +
    '</div>' +
    '<div class="ov-col ov-latest">' +
      '<div class="ov-latest-lbl">' + t('ov_latest') + '</div>' +
      '<div class="ov-latest-card">' +
        (latest.medal ? '<img class="ov-latest-medal" src="' + esc(latest.medal) + '" alt="medal" data-action="open-lb-single">' : '') +
        '<div>' +
          '<div class="ov-latest-meta">' + fmtDate(latest.date) + ' · ' + esc(locStr(latest)) + '</div>' +
          '<div class="ov-latest-name">' + esc(latest.race_name || locStr(latest)) + '</div>' +
        '</div>' +
        (newPb ? '<div class="ov-pb-pill">' + t('ov_new_pb')(esc(pbDistLabel(newPb))) + '</div>' : '') +
        '<div class="ov-latest-right">' +
          '<div class="ov-latest-time">' + esc(latest.total_time.replace(/^0:/, '')) + '</div>' +
          '<div class="ov-latest-sub">' + esc(latest.distance_km) + ' ' + t('km') + ' · ' + esc(calcPace(latest.distance_km, latest.total_time)) + ' ' + t('min_km') + '</div>' +
        '</div>' +
      '</div>' +
    '</div>';
}

// ── Render: Personal Bests ────────────────────────────────────

function renderPBs() {
  document.getElementById('page-pbs').innerHTML = PERSONAL_BESTS.slice().sort(function(a, b) { return b.distance_km - a.distance_km; }).map(function(pb) {
    var photosHtml = (pb.photos && pb.photos.length > 0)
      ? '<div class="pb-photos"><div class="photos-label">' + t('photos') + '</div>' + photoGrid(pb.photos) + '</div>'
      : '';

    var historyHtml;
    if (pb.previous_records && pb.previous_records.length > 0) {
      historyHtml = '<div class="pb-history"><div class="history-head">' + t('prev_records') + '</div>' +
        pb.previous_records.map(function(r) {
          return '<div class="history-row">' +
            '<div class="history-time">' + esc(r.time) + '</div>' +
            '<div class="history-date">' + fmtDate(r.date) + '</div>' +
            '<div class="history-loc">' + esc(locStr(r)) + '</div>' +
          '</div>';
        }).join('') +
      '</div>';
    } else {
      historyHtml = '<div class="pb-history"><div class="history-head">' + t('prev_records') + '</div>' +
        '<p class="no-photos">' + t('first_time') + '</p></div>';
    }

    var progHtml = '';
    if (pb.previous_records && pb.previous_records.length > 0) {
      var prev = pb.previous_records.slice().sort(function(a, b) { return b.date.localeCompare(a.date); })[0];
      var prevSec = timeToSec(prev.time), curSec = timeToSec(pb.total_time);
      if (prevSec > curSec) {
        var diffSec = prevSec - curSec;
        var pct = (diffSec / prevSec * 100).toFixed(1);
        var mm = Math.floor(diffSec / 60), ss = diffSec % 60;
        var diffFmt = (mm > 0 ? mm + ':' + (ss < 10 ? '0' : '') : '') + (mm > 0 ? ss : ss + 's');
        progHtml = '<span class="pb-prog">−' + diffFmt + ' / −' + pct + '%</span>';
      }
    }

    // Progression bar chart: history + current PB, bar height ∝ time (chipping away)
    var chartHtml = '';
    if (pb.previous_records && pb.previous_records.length >= 2) {
      var bars = pb.previous_records.slice()
        .sort(function(a, b) { return a.date.localeCompare(b.date); })
        .map(function(r) { return { sec: timeToSec(r.time), year: r.date.slice(0, 4) }; });
      bars.push({ sec: timeToSec(pb.total_time), year: pb.date.slice(0, 4), pb: true });
      var maxSec = Math.max.apply(null, bars.map(function(b) { return b.sec; }));
      var span   = parseInt(bars[bars.length - 1].year, 10) - parseInt(bars[0].year, 10);
      var nBars  = bars.length;
      chartHtml = '<div class="pbp-wrap">' +
        '<div class="pbp-label">' + t('pbp_label')(span) + '</div>' +
        '<div class="pbp-bars">' +
        bars.map(function(b, bi) {
          var h   = Math.max(18, Math.round(b.sec / maxSec * 100));
          var cls = b.pb ? 'pb' : (bi < (nBars - 1) / 2 ? 'old' : 'mid');
          return '<div class="pbp-col">' +
            '<div class="pbp-bar ' + cls + '" style="height:' + h + 'px">' +
              (b.pb ? '<div class="pbp-pblabel">PB</div>' : '') +
            '</div>' +
            '<div class="pbp-year' + (b.pb ? ' pb' : '') + '">’' + b.year.slice(2) + '</div>' +
          '</div>';
        }).join('') +
        '</div></div>';
    }

    var pbVideo = safeUrl(pb.video);

    return '<article class="pb-card">' +
      '<div class="pb-head">' +
        '<div class="pb-dist-name">' + esc(pbDistLabel(pb)) + '</div>' +
        (pb.race_name ? '<div class="pb-race">' + esc(pb.race_name) + '</div>' : '') +
        '<div style="display:flex;align-items:center;gap:10px;">' +
          '<div class="pb-time">' + esc(pb.total_time) + '</div>' +
          progHtml +
        '</div>' +
      '</div>' +

      '<div class="pb-stats">' +
        '<div class="pb-stat"><div class="stat-label">' + t('date_place') + '</div>' +
          '<div class="stat-value" style="font-size:14px;font-weight:700;">' + fmtDate(pb.date) + '</div>' +
          '<div class="stat-sub">' + esc(locStr(pb)) + '</div></div>' +
        '<div class="pb-stat"><div class="stat-label">' + t('pace') + '</div>' +
          '<div class="stat-value">' + esc(calcPace(pb.distance_km, pb.total_time)) + '</div>' +
          '<div class="stat-sub">' + t('min_km') + '</div></div>' +
        '<div class="pb-stat"><div class="stat-label">' + t('heart_rate') + '</div>' +
          '<div class="stat-value">' + esc(pb.hr_avg || '--') + (pb.hr_avg ? ' <span style="font-size:11px;color:var(--muted);font-weight:600">' + t('avg') + '</span>' : '') + '</div>' +
          '<div class="stat-sub">' + (pb.hr_max ? t('max') + ' ' + esc(pb.hr_max) + ' ' + t('bpm') : '--') + '</div></div>' +
      '</div>' +

      chartHtml +

      '<div style="padding:12px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;">' +
        '<span class="stat-label" style="margin:0">' + t('sneakers') + '</span>' +
        '<span style="font-size:14px;font-weight:700;">' + esc(pb.sneakers) + '</span>' +
      '</div>' +

      (pbVideo ? '<div style="padding:10px 24px;border-bottom:1px solid var(--border)">' +
        '<span class="stat-label" style="margin:0">' + t('video') + '</span> ' +
        '<a href="' + esc(pbVideo) + '" target="_blank" rel="noopener" style="font-size:14px">' + esc(pbVideo) + '</a>' +
      '</div>' : '') +

      photosHtml +
      historyHtml +
    '</article>';
  }).join('');
}

// ── Activities ────────────────────────────────────────────────

function initActivitiesControls() {
  document.getElementById('act-search').placeholder  = t('act_search_ph');
  document.getElementById('actl-type').textContent   = t('act_type_lbl');
  document.getElementById('actl-metric').textContent = t('act_metric_lbl');
  document.getElementById('actl-period').textContent = t('act_period_lbl');
  document.getElementById('aom-distance').textContent        = t('act_metric_dist');
  document.getElementById('aom-runs').textContent            = t('act_metric_runs');
  document.getElementById('aom-time').textContent            = t('act_metric_time');
  document.getElementById('aop-week').textContent            = t('act_period_week');
  document.getElementById('aop-curr_month').textContent      = t('act_period_curr_month');
  document.getElementById('aop-last_month').textContent      = t('act_period_last_month');
  document.getElementById('aop-curr_year').textContent       = t('act_period_curr_year');
  document.getElementById('aop-last_year').textContent       = t('act_period_last_year');
  document.getElementById('aop-custom').textContent          = t('act_period_custom');
  document.getElementById('aop-all').textContent             = t('act_period_all');

  var sel = document.getElementById('act-type');
  var cur = sel.value || 'all';
  var types = [...new Set(ACTIVITIES.map(function(a) { return a.type; }))].sort();
  sel.innerHTML = '<option value="all">' + t('act_all_running') + '</option>' +
    types.map(function(tp) { return '<option value="' + esc(tp) + '">' + esc(tp) + '</option>'; }).join('');
  if (cur !== 'all' && types.indexOf(cur) !== -1) sel.value = cur;

  initCmpControls();
  applyChartToggleState();
}

function getActBounds() {
  var period = document.getElementById('act-period').value;
  var now    = new Date();
  var end    = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
  var start;
  if (period === 'week') {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
  } else if (period === 'curr_month') {
    start = new Date(now.getFullYear(), now.getMonth(), 1);
  } else if (period === 'last_month') {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 29);
  } else if (period === 'curr_year') {
    start = new Date(now.getFullYear(), 0, 1);
  } else if (period === 'last_year') {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 364);
  } else if (period === 'all') {
    start = new Date(0);
  } else {
    var from = document.getElementById('act-from').value;
    var to   = document.getElementById('act-to').value;
    start = from ? new Date(from) : new Date(0);
    end   = to   ? new Date(to + 'T23:59:59') : new Date();
  }
  return { start: start, end: end };
}

function getActFiltered(start, end) {
  var type   = document.getElementById('act-type').value;
  var search = (document.getElementById('act-search').value || '').trim().toLowerCase();
  return ACTIVITIES.filter(function(a) {
    var d = new Date(a.date + 'T12:00:00');
    if (d < start || d > end) return false;
    if (type !== 'all' && a.type !== type) return false;
    if (search && a.type.toLowerCase().indexOf(search) === -1 && a.date.indexOf(search) === -1) return false;
    return true;
  });
}

function buildYearJumps() {
  var years = {};
  ACTIVITIES.forEach(function(a) { years[a.date.slice(0, 4)] = true; });
  var sorted = Object.keys(years).sort().reverse();
  var wrap = document.getElementById('act-year-jumps');
  wrap.innerHTML = sorted.map(function(y) {
    return '<button class="act-year-btn" data-action="jump-year" data-year="' + y + '">' + y + '</button>';
  }).join('');
}

function jumpToYear(y) {
  document.getElementById('act-period').value = 'custom';
  document.getElementById('act-custom-wrap').style.display = '';
  document.getElementById('act-from').value = y + '-01-01';
  document.getElementById('act-to').value   = y + '-12-31';
  document.querySelectorAll('.act-year-btn').forEach(function(b) {
    b.classList.toggle('active', b.textContent === y);
  });
  renderActivities();
}

function clearYearActive() {
  document.querySelectorAll('.act-year-btn').forEach(function(b) { b.classList.remove('active'); });
}

function actTimeToMin(s) {
  var p = s.split(':').map(Number);
  return p.length === 3 ? p[0] * 60 + p[1] + p[2] / 60 : p[0] + p[1] / 60;
}

function fmtActTotalTime(min) {
  var h = Math.floor(min / 60), m = Math.round(min % 60);
  if (h > 0) return h + t('act_h') + (m > 0 ? ' ' + m + t('act_min') : '');
  return m + t('act_min');
}

function localDateStr(d) {
  var y = d.getFullYear();
  var m = String(d.getMonth() + 1).padStart(2, '0');
  var day = String(d.getDate()).padStart(2, '0');
  return y + '-' + m + '-' + day;
}

function getActBucketKey(dateStr, bType) {
  if (bType === 'year')  return dateStr.slice(0, 4);
  if (bType === 'month') return dateStr.slice(0, 7);
  if (bType === 'day')   return dateStr;
  var d = new Date(dateStr + 'T12:00:00');
  var dow = d.getDay() || 7;
  d.setDate(d.getDate() - (dow - 1));
  return localDateStr(d);
}

function genActBucketKeys(start, end, bType) {
  var keys = [], cur;
  if (bType === 'day') {
    cur = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    while (cur <= end) {
      keys.push(localDateStr(cur));
      cur.setDate(cur.getDate() + 1);
    }
  } else if (bType === 'year') {
    cur = new Date(start.getFullYear(), 0, 1);
    while (cur <= end) {
      keys.push(String(cur.getFullYear()));
      cur.setFullYear(cur.getFullYear() + 1);
    }
  } else if (bType === 'month') {
    cur = new Date(start.getFullYear(), start.getMonth(), 1);
    while (cur <= end) {
      keys.push(cur.getFullYear() + '-' + String(cur.getMonth() + 1).padStart(2, '0'));
      cur.setMonth(cur.getMonth() + 1);
    }
  } else {
    cur = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    var dow = cur.getDay() || 7;
    cur.setDate(cur.getDate() - (dow - 1));
    while (cur <= end) {
      keys.push(localDateStr(cur));
      cur.setDate(cur.getDate() + 7);
    }
  }
  return keys;
}

function fmtActBucketLabel(key, bType) {
  if (bType === 'year') return key;
  if (bType === 'month') {
    var d = new Date(key + '-01T12:00:00');
    return LANG === 'be' ? BE_MONTHS_SHORT[d.getMonth()]
                         : d.toLocaleDateString('en-GB', { month: 'short' });
  }
  var d = new Date(key + 'T12:00:00');
  var mon = LANG === 'be' ? BE_MONTHS_SHORT[d.getMonth()]
                          : d.toLocaleDateString('en-GB', { month: 'short' });
  return bType === 'day' ? String(d.getDate()) : mon + ' ' + d.getDate();
}

function onActPeriodChange() {
  var val = document.getElementById('act-period').value;
  document.getElementById('act-custom-wrap').style.display = val === 'custom' ? 'flex' : 'none';
  if (val !== 'custom') clearYearActive();
  renderActivities();
}

function renderActChart(acts, bounds) {
  var svg    = document.getElementById('act-svg');
  var metric = document.getElementById('act-metric').value;
  var days   = Math.round((bounds.end - bounds.start) / 86400000);
  var bType  = days <= 31 ? 'day' : days <= 90 ? 'week' : days <= 1095 ? 'month' : 'year';
  var keys   = genActBucketKeys(bounds.start, bounds.end, bType);

  var map = {};
  keys.forEach(function(k) { map[k] = { n: 0, dist: 0, time: 0 }; });
  acts.forEach(function(a) {
    var k = getActBucketKey(a.date, bType);
    if (map[k]) { map[k].n++; map[k].dist += a.distance_km; map[k].time += actTimeToMin(a.time); }
  });

  if (bType === 'year') {
    keys = keys.filter(function(k) { return map[k].n > 0; });
  }

  var vals = keys.map(function(k) {
    return metric === 'distance' ? map[k].dist
         : metric === 'runs'     ? map[k].n
         : map[k].time / 60;
  });

  var maxV = Math.max.apply(null, vals) || 1;
  var W = 760, H = 160, ML = 46, MR = 12, MT = 10, MB = 30;
  var cW = W - ML - MR, cH = H - MT - MB;
  var n = keys.length;
  var slotW = cW / n;
  var barW  = Math.min(36, Math.max(4, slotW * 0.7));

  var yHtml = '';
  for (var ti = 0; ti <= 3; ti++) {
    var tv = (ti / 3) * maxV;
    var ty = MT + cH - (tv / maxV) * cH;
    var lbl = metric === 'distance' ? tv.toFixed(1)
            : metric === 'runs'     ? Math.round(tv).toString()
            : tv.toFixed(1);
    yHtml += '<line x1="' + ML + '" y1="' + ty + '" x2="' + (ML + cW) + '" y2="' + ty +
             '" stroke="var(--border)" stroke-width="1"/>' +
             '<text x="' + (ML - 5) + '" y="' + (ty + 4) +
             '" text-anchor="end" font-size="10" font-family="inherit" fill="var(--muted)">' + lbl + '</text>';
  }

  var barsHtml = '', xHtml = '';
  var labelEvery = Math.ceil(n / 12);
  keys.forEach(function(k, i) {
    var v  = vals[i];
    var cx = ML + (i + 0.5) * slotW;
    if (v > 0) {
      var bh = (v / maxV) * cH, by = MT + cH - bh;
      var tipVal = metric === 'distance' ? v.toFixed(1) + ' km'
                 : metric === 'runs'     ? v + (v !== 1 ? ' runs' : ' run')
                 : fmtActTotalTime(v * 60);
      barsHtml += '<rect x="' + (cx - barW / 2) + '" y="' + by + '" width="' + barW + '" height="' + bh +
                  '" rx="3" fill="var(--accent)" opacity="0.85">' +
                  '<title>' + fmtActBucketLabel(k, bType) + ': ' + tipVal + '</title></rect>';
    }
    if (i % labelEvery === 0 || i === n - 1) {
      xHtml += '<text x="' + cx + '" y="' + (MT + cH + 16) +
               '" text-anchor="middle" font-size="10" font-family="inherit" fill="var(--muted)">' +
               fmtActBucketLabel(k, bType) + '</text>';
    }
  });

  svg.innerHTML = yHtml + barsHtml + xHtml;
}

function fmtPeriodDuration(days) {
  var yrs = Math.floor(days / 365);
  var rem = days - yrs * 365;
  var mos = Math.floor(rem / 30);
  var ds  = rem - mos * 30;
  var parts = [];
  if (yrs > 0) parts.push(yrs + ' ' + t('act_yr'));
  if (mos > 0) parts.push(mos + ' ' + t('act_mo'));
  if (ds  > 0 || parts.length === 0) parts.push(ds + ' ' + t('act_d'));
  return parts.join(' ');
}

function renderActList(acts, bounds) {
  var el = document.getElementById('act-list');
  if (acts.length === 0) {
    el.innerHTML = '<p style="color:var(--muted);font-size:14px;text-align:center;padding:32px 0">' +
                   t('act_no_data') + '</p>';
    return;
  }
  var sorted = acts.slice().sort(function(a, b) { return b.datetime.localeCompare(a.datetime); });
  var totalDist = 0, totalMin = 0;
  sorted.forEach(function(a) { totalDist += a.distance_km; totalMin += actTimeToMin(a.time); });

  // Compute period span
  var periodStart = bounds ? bounds.start : null;
  var periodEnd   = bounds ? bounds.end   : null;
  // For "all years" the start is epoch (new Date(0)); use actual activity dates instead
  if (periodStart && periodStart.getTime() === 0 && sorted.length > 0) {
    var dates = sorted.map(function(a) { return new Date(a.date); });
    periodStart = new Date(Math.min.apply(null, dates));
    periodEnd   = new Date(Math.max.apply(null, dates));
  }
  var periodDays = 0;
  if (periodStart && periodEnd) {
    periodDays = Math.round((periodEnd - periodStart) / 86400000);
  }

  var summaryHtml =
    '<div class="act-summary">' +
      '<div class="act-sum-item"><span class="act-sum-val">' + sorted.length + '</span>' +
        '<span class="act-sum-lbl">' + t('act_metric_runs') + '</span></div>' +
      '<div class="act-sum-item"><span class="act-sum-val">' + totalDist.toFixed(1) + '</span>' +
        '<span class="act-sum-lbl">' + t('km') + '</span></div>' +
      '<div class="act-sum-item"><span class="act-sum-val">' + fmtActTotalTime(totalMin) + '</span>' +
        '<span class="act-sum-lbl">' + t('total_time') + '</span></div>' +
      (periodDays > 0
        ? '<div class="act-sum-item"><span class="act-sum-val">' + fmtPeriodDuration(periodDays) + '</span>' +
            '<span class="act-sum-lbl">' + t('act_period_duration') + '</span></div>'
        : '') +
      (periodDays >= 7
        ? '<div class="act-sum-item"><span class="act-sum-val">' + (totalDist / (periodDays / 7)).toFixed(1) + '</span>' +
            '<span class="act-sum-lbl">' + t('act_avg_week') + '</span></div>'
        : '') +
      (periodDays >= 30
        ? '<div class="act-sum-item"><span class="act-sum-val">' + (totalDist / (periodDays / 30)).toFixed(1) + '</span>' +
            '<span class="act-sum-lbl">' + t('act_avg_month') + '</span></div>'
        : '') +
      (periodDays >= 365
        ? '<div class="act-sum-item"><span class="act-sum-val">' + (totalDist / (periodDays / 365)).toFixed(1) + '</span>' +
            '<span class="act-sum-lbl">' + t('act_avg_year') + '</span></div>'
        : '') +
    '</div>';

  var listHtml = sorted.map(function(a) {
    var pace       = a.distance_km > 0 ? calcPace(a.distance_km, a.time) : '--';
    var elevHtml   = a.elevation > 0
      ? '<div class="act-stat"><span class="act-stat-val">' + esc(a.elevation) + '</span>' +
        '<span class="act-stat-lbl">' + t('elevation') + ', ' + t('m') + '</span></div>'
      : '';
    var typeClass  = a.type.toLowerCase().indexOf('trail') !== -1 ? ' trail' : '';
    return '<div class="act-row">' +
      '<div style="min-width:110px;font-size:13px;color:var(--muted);font-weight:600">' + fmtDate(a.date) + '</div>' +
      '<span class="act-type' + typeClass + '">' + esc(a.type) + '</span>' +
      '<div class="act-stat"><span class="act-stat-val">' + esc(a.distance_km.toFixed(2)) + '</span>' +
        '<span class="act-stat-lbl">' + t('km') + '</span></div>' +
      '<div class="act-stat"><span class="act-stat-val">' + esc(a.time) + '</span>' +
        '<span class="act-stat-lbl">' + t('total_time') + '</span></div>' +
      '<div class="act-stat"><span class="act-stat-val">' + esc(pace) + '</span>' +
        '<span class="act-stat-lbl">' + t('min_km') + '</span></div>' +
      elevHtml +
    '</div>';
  }).join('');

  el.innerHTML = summaryHtml + listHtml;
}

function renderActivities() {
  var bounds = getActBounds();
  var acts   = getActFiltered(bounds.start, bounds.end);
  renderActChart(acts, bounds);
  renderActList(acts, bounds);
  renderCmpChart();
}

function toggleActChart() {
  var body = document.getElementById('act-chart-body');
  var btn  = document.getElementById('act-chart-toggle');
  var hidden = body.style.display === 'none';
  body.style.display = hidden ? '' : 'none';
  btn.textContent = hidden ? '▾' : '▸';
  localStorage.setItem('actChartHidden', hidden ? '' : '1');
}
function toggleCmpChart() {
  var body = document.getElementById('cmp-chart-body');
  var btn  = document.getElementById('cmp-chart-toggle');
  var hidden = body.style.display === 'none';
  body.style.display = hidden ? '' : 'none';
  btn.textContent = hidden ? '▾' : '▸';
  localStorage.setItem('cmpChartHidden', hidden ? '' : '1');
}
function applyChartToggleState() {
  if (localStorage.getItem('actChartHidden') === '1') {
    document.getElementById('act-chart-body').style.display = 'none';
    document.getElementById('act-chart-toggle').textContent = '▸';
  }
  if (localStorage.getItem('cmpChartHidden') === '1') {
    document.getElementById('cmp-chart-body').style.display = 'none';
    document.getElementById('cmp-chart-toggle').textContent = '▸';
  }
}

// ── Comparison chart ──────────────────────────────────────────

var EN_DAYS_SHORT = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
var BE_DAYS_SHORT = ['Нд','Пн','Аў','Ср','Чц','Пт','Сб'];
var EN_MONTHS_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function initCmpControls() {
  document.getElementById('cmpl-title').textContent  = t('cmp_lbl');
  document.getElementById('cmpl-period').textContent = t('cmp_period_lbl');
  document.getElementById('cop-week').textContent    = t('cmp_week');
  document.getElementById('cop-month').textContent   = t('cmp_month');
  document.getElementById('cop-year').textContent    = t('cmp_year');
  document.getElementById('cop-custom').textContent  = t('cmp_custom');
  document.getElementById('cmpl-p1').textContent     = t('cmp_p1');
  document.getElementById('cmpl-p2').textContent     = t('cmp_p2');
}

function onCmpPeriodChange() {
  document.getElementById('cmp-custom-wrap').style.display =
    document.getElementById('cmp-period').value === 'custom' ? 'flex' : 'none';
  renderCmpChart();
}

function getCmpBounds() {
  var period = document.getElementById('cmp-period').value;
  var now = new Date();
  var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  var p1s, p1e, p2s, p2e, bType, n;

  if (period === 'week') {
    p1e = new Date(today); p1e.setHours(23,59,59);
    p1s = new Date(today); p1s.setDate(today.getDate() - 6);
    p2e = new Date(today); p2e.setDate(today.getDate() - 7); p2e.setHours(23,59,59);
    p2s = new Date(today); p2s.setDate(today.getDate() - 13);
    bType = 'day'; n = 7;
  } else if (period === 'month') {
    p1e = new Date(today); p1e.setHours(23,59,59);
    p1s = new Date(today); p1s.setDate(today.getDate() - 29);
    p2e = new Date(today); p2e.setDate(today.getDate() - 30); p2e.setHours(23,59,59);
    p2s = new Date(today); p2s.setDate(today.getDate() - 59);
    bType = 'day'; n = 30;
  } else if (period === 'year') {
    p1e = new Date(today); p1e.setHours(23,59,59);
    p1s = new Date(today); p1s.setDate(today.getDate() - 364);
    p2e = new Date(today); p2e.setDate(today.getDate() - 365); p2e.setHours(23,59,59);
    p2s = new Date(today); p2s.setDate(today.getDate() - 729);
    bType = 'month'; n = 12;
  } else {
    var f1 = document.getElementById('cmp-p1-from').value;
    var t1 = document.getElementById('cmp-p1-to').value;
    var f2 = document.getElementById('cmp-p2-from').value;
    var t2 = document.getElementById('cmp-p2-to').value;
    if (!f1 || !t1 || !f2 || !t2) return null;
    p1s = new Date(f1); p1e = new Date(t1 + 'T23:59:59');
    p2s = new Date(f2); p2e = new Date(t2 + 'T23:59:59');
    var days = Math.round((p1e - p1s) / 86400000);
    if (days <= 31)       { bType = 'day';   n = days + 1; }
    else if (days <= 90)  { bType = 'week';  n = Math.ceil((days + 1) / 7); }
    else                  { bType = 'month';
      var sm = p1s.getFullYear() * 12 + p1s.getMonth();
      var em = p1e.getFullYear() * 12 + p1e.getMonth();
      n = em - sm + 1;
    }
  }
  return { p1s: p1s, p1e: p1e, p2s: p2s, p2e: p2e, bType: bType, n: n };
}

function cmpBucketActs(acts, pstart, bType, n) {
  var metric = document.getElementById('act-metric').value;
  var vals = new Array(n).fill(0);
  acts.forEach(function(a) {
    var d = new Date(a.date + 'T12:00:00');
    var idx;
    if (bType === 'day') {
      idx = Math.round((d - pstart) / 86400000);
    } else if (bType === 'week') {
      idx = Math.floor((d - pstart) / (7 * 86400000));
    } else {
      var sm = pstart.getFullYear() * 12 + pstart.getMonth();
      idx = (d.getFullYear() * 12 + d.getMonth()) - sm;
    }
    if (idx >= 0 && idx < n) {
      if (metric === 'distance')    vals[idx] += a.distance_km;
      else if (metric === 'runs')   vals[idx]++;
      else                          vals[idx] += actTimeToMin(a.time) / 60;
    }
  });
  return vals;
}

function cmpXLabel(i, p1s, bType, period) {
  if (bType === 'day') {
    if (period === 'week') {
      var di = (p1s.getDay() + i) % 7;
      return LANG === 'be' ? BE_DAYS_SHORT[di] : EN_DAYS_SHORT[di];
    }
    return String(i + 1);
  }
  if (bType === 'week') return String(i + 1);
  var mi = (p1s.getMonth() + i) % 12;
  return LANG === 'be' ? BE_MONTHS_SHORT[mi] : EN_MONTHS_SHORT[mi];
}

function cmpFmtRange(s, e) {
  var mo = LANG === 'be' ? BE_MONTHS_SHORT : EN_MONTHS_SHORT;
  var fs = s.getDate() + ' ' + mo[s.getMonth()];
  var fe = e.getDate() + ' ' + mo[e.getMonth()];
  if (s.getFullYear() !== e.getFullYear()) fs += ' ' + s.getFullYear();
  return fs + ' – ' + fe + ' ' + e.getFullYear();
}

function renderCmpChart() {
  var svg    = document.getElementById('cmp-svg');
  var legend = document.getElementById('cmp-legend');
  var bounds = getCmpBounds();
  if (!bounds) { svg.innerHTML = ''; legend.innerHTML = ''; return; }

  var period = document.getElementById('cmp-period').value;
  var metric = document.getElementById('act-metric').value;
  var acts1  = getActFiltered(bounds.p1s, bounds.p1e);
  var acts2  = getActFiltered(bounds.p2s, bounds.p2e);
  var vals1  = cmpBucketActs(acts1, bounds.p1s, bounds.bType, bounds.n);
  var vals2  = cmpBucketActs(acts2, bounds.p2s, bounds.bType, bounds.n);

  legend.innerHTML =
    '<span class="cmp-leg-item"><span class="cmp-leg-dot" style="background:var(--accent)"></span>' + cmpFmtRange(bounds.p1s, bounds.p1e) + '</span>' +
    '<span class="cmp-leg-item"><span class="cmp-leg-dot" style="background:#5b8def"></span>' + cmpFmtRange(bounds.p2s, bounds.p2e) + '</span>';

  var maxV = Math.max(Math.max.apply(null, vals1), Math.max.apply(null, vals2)) || 1;
  var W = 760, H = 160, ML = 46, MR = 12, MT = 10, MB = 30;
  var cW = W - ML - MR, cH = H - MT - MB;
  var n = bounds.n;
  var slotW = cW / n;
  var barW  = Math.min(18, Math.max(2, slotW * 0.3));
  var gap   = Math.max(1, barW * 0.3);

  var yHtml = '';
  for (var ti = 0; ti <= 3; ti++) {
    var tv = (ti / 3) * maxV;
    var ty = MT + cH - (tv / maxV) * cH;
    var lbl = metric === 'runs' ? Math.round(tv).toString() : tv.toFixed(1);
    yHtml += '<line x1="' + ML + '" y1="' + ty + '" x2="' + (ML + cW) + '" y2="' + ty +
             '" stroke="var(--border)" stroke-width="1"/>' +
             '<text x="' + (ML - 5) + '" y="' + (ty + 4) +
             '" text-anchor="end" font-size="10" font-family="inherit" fill="var(--muted)">' + lbl + '</text>';
  }

  var barsHtml = '', xHtml = '';
  var labelEvery = Math.ceil(n / 12);
  for (var i = 0; i < n; i++) {
    var cx    = ML + (i + 0.5) * slotW;
    var bar1x = cx - barW - gap / 2;
    var bar2x = cx + gap / 2;

    if (vals1[i] > 0) {
      var bh = (vals1[i] / maxV) * cH, by = MT + cH - bh;
      barsHtml += '<rect x="' + bar1x + '" y="' + by + '" width="' + barW + '" height="' + bh +
                  '" rx="2" fill="var(--accent)" opacity="0.85">' +
                  '<title>' + cmpXLabel(i, bounds.p1s, bounds.bType, period) + ' (' + cmpFmtRange(bounds.p1s, bounds.p1e) + '): ' + vals1[i].toFixed(metric === 'runs' ? 0 : 1) + '</title></rect>';
    }
    if (vals2[i] > 0) {
      var bh2 = (vals2[i] / maxV) * cH, by2 = MT + cH - bh2;
      barsHtml += '<rect x="' + bar2x + '" y="' + by2 + '" width="' + barW + '" height="' + bh2 +
                  '" rx="2" fill="#5b8def" opacity="0.85">' +
                  '<title>' + cmpXLabel(i, bounds.p1s, bounds.bType, period) + ' (' + cmpFmtRange(bounds.p2s, bounds.p2e) + '): ' + vals2[i].toFixed(metric === 'runs' ? 0 : 1) + '</title></rect>';
    }
    if (i % labelEvery === 0 || i === n - 1) {
      xHtml += '<text x="' + cx + '" y="' + (MT + cH + 16) +
               '" text-anchor="middle" font-size="10" font-family="inherit" fill="var(--muted)">' +
               cmpXLabel(i, bounds.p1s, bounds.bType, period) + '</text>';
    }
  }

  svg.innerHTML = yHtml + barsHtml + xHtml;
}

// ── Language switch ───────────────────────────────────────────

function toggleNav() {
  var nav    = document.getElementById('main-nav');
  var burger = document.getElementById('burger');
  var open   = nav.classList.toggle('open');
  burger.classList.toggle('open', open);
  burger.setAttribute('aria-expanded', open ? 'true' : 'false');
}

function closeNav() {
  document.getElementById('main-nav').classList.remove('open');
  var burger = document.getElementById('burger');
  burger.classList.remove('open');
  burger.setAttribute('aria-expanded', 'false');
}

function toggleTheme() {
  var dark = document.documentElement.classList.toggle('dark');
  document.getElementById('theme-toggle').textContent = dark ? '☽' : '☀';
  localStorage.setItem('theme', dark ? 'dark' : 'light');
}
(function() {
  if (localStorage.getItem('theme') === 'dark') {
    document.documentElement.classList.add('dark');
    document.getElementById('theme-toggle').textContent = '☽';
  }
})();

function setLang(lang) {
  LANG = lang;
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;

  document.getElementById('lang-en').classList.toggle('active', lang === 'en');
  document.getElementById('lang-be').classList.toggle('active', lang === 'be');
  document.getElementById('logo').innerHTML      = t('logo');
  document.getElementById('nav-overview').textContent    = t('nav_overview');
  document.getElementById('nav-runs').textContent        = t('nav_runs');
  document.getElementById('nav-pbs').textContent         = t('nav_pbs');
  document.getElementById('nav-activities').textContent  = t('nav_activities');

  renderOverview();
  buildFilterOptions();
  applyFilters();
  buildPBChartOptions();
  renderPBChart();
  renderPBs();
  initActivitiesControls();
  renderActivities();
}

// ── Interactions ──────────────────────────────────────────────

function showPage(name, btn) {
  document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('visible'); });
  document.querySelectorAll('nav button').forEach(function(b) { b.classList.remove('active'); });
  document.getElementById('page-' + name).classList.add('visible');
  btn.classList.add('active');
  document.getElementById('runs-filterbar').style.display = name === 'runs' ? ''      : 'none';
  document.getElementById('runs-count-bar').style.display = name === 'runs' ? ''      : 'none';
  document.getElementById('pbs-chart').style.display      = name === 'pbs'  ? 'block' : 'none';
  if (name === 'overview')   { renderOverview(); }
  if (name === 'activities') { initActivitiesControls(); buildYearJumps(); renderActivities(); }
  closeNav();
}

var _lbSet = [], _lbIdx = 0;

function openLb(setId, idx) {
  _lbSet = (photoGrid._sets && photoGrid._sets[setId]) || [];
  _lbIdx = idx || 0;
  _lbShow();
}
function openLbSingle(src) {
  _lbSet = [src];
  _lbIdx = 0;
  _lbShow();
}
function _lbShow() {
  document.getElementById('lb-img').src = _lbSet[_lbIdx];
  document.getElementById('lightbox').classList.add('open');
  document.getElementById('lb-prev').classList.toggle('hidden', _lbIdx === 0);
  document.getElementById('lb-next').classList.toggle('hidden', _lbIdx === _lbSet.length - 1);
}
function lbNav(dir) {
  var next = _lbIdx + dir;
  if (next >= 0 && next < _lbSet.length) { _lbIdx = next; _lbShow(); }
}
function closeLb() {
  document.getElementById('lightbox').classList.remove('open');
  document.getElementById('lb-img').src = '';
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape')      closeLb();
  if (e.key === 'ArrowLeft')   lbNav(-1);
  if (e.key === 'ArrowRight')  lbNav(1);
});

// ── Event wiring (CSP-safe: no inline handlers) ───────────────
function initEvents() {
  var byId = function(id) { return document.getElementById(id); };

  byId('nav-overview').addEventListener('click', function() { showPage('overview', this); });
  byId('nav-runs').addEventListener('click', function() { showPage('runs', this); });
  byId('nav-pbs').addEventListener('click', function() { showPage('pbs', this); });
  byId('nav-activities').addEventListener('click', function() { showPage('activities', this); });

  byId('theme-toggle').addEventListener('click', toggleTheme);
  byId('lang-en').addEventListener('click', function() { setLang('en'); });
  byId('lang-be').addEventListener('click', function() { setLang('be'); });
  byId('burger').addEventListener('click', toggleNav);

  byId('lightbox').addEventListener('click', closeLb);
  byId('lb-close').addEventListener('click', function(e) { e.stopPropagation(); closeLb(); });
  byId('lb-prev').addEventListener('click', function(e) { e.stopPropagation(); lbNav(-1); });
  byId('lb-next').addEventListener('click', function(e) { e.stopPropagation(); lbNav(1); });
  byId('lb-img').addEventListener('click', function(e) { e.stopPropagation(); });

  byId('filter-year').addEventListener('change', applyFilters);
  byId('filter-distance').addEventListener('change', applyFilters);
  byId('filter-dist-custom').addEventListener('input', applyFilters);
  byId('filter-search').addEventListener('input', onSearchInput);
  byId('filter-race').addEventListener('input', onRaceInput);
  byId('filter-trail').addEventListener('change', applyFilters);
  byId('filter-reset').addEventListener('click', resetFilters);

  byId('pbc-distance').addEventListener('change', renderPBChart);
  byId('pbc-pace').addEventListener('click', function() { setPBChartMetric('pace'); });
  byId('pbc-time').addEventListener('click', function() { setPBChartMetric('time'); });
  byId('pbc-toggle').addEventListener('click', togglePBChart);

  byId('act-chart-toggle').addEventListener('click', toggleActChart);
  byId('act-type').addEventListener('change', renderActivities);
  byId('act-metric').addEventListener('change', renderActivities);
  byId('act-period').addEventListener('change', onActPeriodChange);
  byId('act-from').addEventListener('change', renderActivities);
  byId('act-to').addEventListener('change', renderActivities);
  byId('act-search').addEventListener('input', renderActivities);
  byId('cmp-chart-toggle').addEventListener('click', toggleCmpChart);
  byId('cmp-period').addEventListener('change', onCmpPeriodChange);
  byId('cmp-p1-from').addEventListener('change', renderCmpChart);
  byId('cmp-p1-to').addEventListener('change', renderCmpChart);
  byId('cmp-p2-from').addEventListener('change', renderCmpChart);
  byId('cmp-p2-to').addEventListener('change', renderCmpChart);

  // Delegated handlers for dynamically-rendered content
  document.addEventListener('click', function(e) {
    var el = e.target.closest('[data-action]');
    if (!el) return;
    var act = el.getAttribute('data-action');
    if (act === 'open-lb') {
      openLb(el.getAttribute('data-set'), parseInt(el.getAttribute('data-idx'), 10) || 0);
    } else if (act === 'open-lb-single') {
      e.stopPropagation();
      openLbSingle(el.getAttribute('src'));
    } else if (act === 'show-runs') {
      showPage('runs', document.getElementById('nav-runs'));
    } else if (act === 'jump-year') {
      jumpToYear(el.getAttribute('data-year'));
    }
  });
}

// ── Init ─────────────────────────────────────────────────────
initEvents();
setLang(LANG);
