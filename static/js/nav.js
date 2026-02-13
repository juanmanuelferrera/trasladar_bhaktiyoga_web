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

    // Mobile dropdown accordion
    var dropdownParents = document.querySelectorAll('.has-dropdown > a');
    for (var i = 0; i < dropdownParents.length; i++) {
        dropdownParents[i].addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                var li = this.parentElement;
                var wasOpen = li.classList.contains('dropdown-open');

                // Close all other open dropdowns (accordion)
                var allOpen = document.querySelectorAll('.has-dropdown.dropdown-open');
                for (var j = 0; j < allOpen.length; j++) {
                    allOpen[j].classList.remove('dropdown-open');
                    var a = allOpen[j].querySelector('a[aria-haspopup]');
                    if (a) a.setAttribute('aria-expanded', 'false');
                }

                // Toggle this one
                if (!wasOpen) {
                    li.classList.add('dropdown-open');
                    this.setAttribute('aria-expanded', 'true');
                }
            }
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
