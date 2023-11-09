document.addEventListener("DOMContentLoaded", function () {
    display_cur_time(); // Display the time immediately

    setInterval(display_cur_time, 1000); // Update the time every second
});

function display_cur_time() {
    var x = new Date();
    var ampm = x.getHours() >= 12 ? ' PM' : ' AM';
    var hours = x.getHours() % 12;
    hours = hours ? hours : 12;
    var minutes = x.getMinutes();
    var seconds = x.getSeconds();

    var timeString =
        hours.toString().padStart(2, '0') + ":" +
        minutes.toString().padStart(2, '0') + " " +
        ampm;

    var ctElement = document.getElementById('ct');
    if (ctElement) {
        ctElement.textContent = timeString;
        ctElement.classList.add('time-display'); // Apply the CSS class
    }
}
