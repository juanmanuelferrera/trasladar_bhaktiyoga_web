// Mobile navigation toggle
(function() {
    var toggle = document.querySelector('.mobile-toggle');
    var nav = document.getElementById('mainNav');

    if (toggle && nav) {
        toggle.addEventListener('click', function() {
            nav.classList.toggle('open');
            toggle.classList.toggle('active');
            var expanded = nav.classList.contains('open');
            toggle.setAttribute('aria-expanded', expanded);
        });
    }

    // Close mobile nav when clicking outside
    document.addEventListener('click', function(e) {
        if (nav && nav.classList.contains('open')) {
            if (!nav.contains(e.target) && !toggle.contains(e.target)) {
                nav.classList.remove('open');
                toggle.classList.remove('active');
                toggle.setAttribute('aria-expanded', 'false');
            }
        }
    });
})();
