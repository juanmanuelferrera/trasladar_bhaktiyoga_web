// Mobile navigation toggle
(function() {
    var toggle = document.querySelector('.mobile-toggle');
    var nav = document.getElementById('mainNav');

    if (toggle && nav) {
        toggle.addEventListener('click', function() {
            nav.classList.toggle('open');
            var expanded = nav.classList.contains('open');
            toggle.setAttribute('aria-expanded', expanded);
        });
    }

    // Close mobile nav when clicking outside
    document.addEventListener('click', function(e) {
        if (nav && nav.classList.contains('open')) {
            if (!nav.contains(e.target) && !toggle.contains(e.target)) {
                nav.classList.remove('open');
                toggle.setAttribute('aria-expanded', 'false');
            }
        }
    });

    // Dropdown toggle for touch devices
    var dropdowns = document.querySelectorAll('.has-dropdown > a');
    dropdowns.forEach(function(link) {
        link.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                var parent = this.parentElement;
                var isOpen = parent.classList.contains('dropdown-open');

                // Close all other dropdowns
                document.querySelectorAll('.has-dropdown').forEach(function(el) {
                    el.classList.remove('dropdown-open');
                });

                if (!isOpen) {
                    e.preventDefault();
                    parent.classList.add('dropdown-open');
                }
            }
        });
    });
})();
