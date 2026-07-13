(function() {
    var searchTimer;

    function initSidebar() {
        var toggle = document.getElementById('sidebarToggle');
        var sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        var overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);

        function showSidebar(show) {
            sidebar.classList.toggle('show', show);
            overlay.classList.toggle('show', show);
        }

        if (toggle) {
            toggle.addEventListener('click', function(e) {
                e.stopPropagation();
                showSidebar(!sidebar.classList.contains('show'));
            });
        }

        overlay.addEventListener('click', function() {
            showSidebar(false);
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') showSidebar(false);
        });

        var menuItems = sidebar.querySelectorAll('.nav-link');
        menuItems.forEach(function(item) {
            item.addEventListener('click', function() {
                if (window.innerWidth < 992) showSidebar(false);
            });
        });
    }

    function initGlobalSearch() {
        var input = document.getElementById('globalSearch');
        var results = document.getElementById('searchResults');
        if (!input || !results) return;

        input.addEventListener('input', function() {
            var q = this.value.trim();
            clearTimeout(searchTimer);
            if (q.length < 2) {
                results.style.display = 'none';
                return;
            }

            searchTimer = setTimeout(function() {
                fetch('/buscar?q=' + encodeURIComponent(q))
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        results.innerHTML = '';
                        if (data.length === 0) {
                            results.innerHTML = '<div class="search-result-item"><span class="text-muted small">Sin resultados</span></div>';
                        } else {
                            data.forEach(function(item) {
                                var el = document.createElement('a');
                                el.href = item.url || '#';
                                el.className = 'search-result-item';

                                var badgeClass = 'bg-secondary';
                                if (item.tipo === 'Cliente') badgeClass = 'bg-primary';
                                else if (item.tipo === 'Producto') badgeClass = 'bg-success';
                                else if (item.tipo === 'Pedido') badgeClass = 'bg-warning text-dark';
                                else if (item.tipo === 'Usuario') badgeClass = 'bg-info text-dark';

                                var detailHtml = '';
                                if (item.email) detailHtml = item.email;
                                else if (item.precio) detailHtml = item.precio + ' | Stock: ' + item.stock;
                                else if (item.cliente) detailHtml = item.cliente + ' | ' + item.total;

                                el.innerHTML = '<span class="badge ' + badgeClass + '">' + item.tipo + '</span>' +
                                    '<div class="result-info">' +
                                    '<div class="result-name">' + item.nombre + '</div>' +
                                    '<div class="result-detail">' + detailHtml + '</div>' +
                                    '</div>';
                                results.appendChild(el);
                            });
                        }
                        results.style.display = 'block';
                    })
                    .catch(function() {
                        results.style.display = 'none';
                    });
            }, 300);
        });

        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !results.contains(e.target)) {
                results.style.display = 'none';
            }
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                results.style.display = 'none';
                input.blur();
            }
        });
    }

    function initConfirmDialogs() {
        document.addEventListener('click', function(e) {
            var btn = e.target.closest('[data-confirm]');
            if (!btn) return;
            var message = btn.getAttribute('data-confirm') || 'Confirmar eliminacion?';
            if (!confirm(message)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });

        document.addEventListener('click', function(e) {
            var btn = e.target.closest('.btn-delete');
            if (!btn) return;
            var name = btn.getAttribute('data-name') || 'este registro';
            if (!confirm('Eliminar ' + name + '? Esta accion no se puede deshacer.')) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }

    function initAutoDismissAlerts() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            setTimeout(function() {
                if (bootstrap && bootstrap.Alert) {
                    var bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            }, 6000);
        });
    }

    function initThemeToggle() {
        var btn = document.getElementById('themeToggle');
        if (!btn) return;

        var saved = localStorage.getItem('comerciotech_theme');
        if (saved === 'light') {
            document.body.classList.add('light-mode');
            btn.innerHTML = '<i class="bi bi-sun"></i>';
        }

        btn.addEventListener('click', function() {
            document.body.classList.toggle('light-mode');
            var isLight = document.body.classList.contains('light-mode');
            localStorage.setItem('comerciotech_theme', isLight ? 'light' : 'dark');
            this.innerHTML = isLight ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
        });
    }

    function initClock() {
        var display = document.getElementById('clockDisplay');
        if (!display || !display.querySelector('span')) return;

        var span = display.querySelector('span');
        setInterval(function() {
            var now = new Date();
            var day = String(now.getDate()).padStart(2, '0');
            var month = String(now.getMonth() + 1).padStart(2, '0');
            var year = now.getFullYear();
            var hours = String(now.getHours()).padStart(2, '0');
            var mins = String(now.getMinutes()).padStart(2, '0');
            span.textContent = day + '/' + month + '/' + year + ' ' + hours + ':' + mins;
        }, 1000);
    }

    function initMongoStatus() {
        fetch('/buscar?q=__ping__')
            .then(function(r) { return true; })
            .catch(function() {
                var dot = document.querySelector('.status-dot-mongo');
                var label = document.getElementById('mongoLabel');
                if (dot) dot.style.background = '#ef4444';
                if (label) label.textContent = 'Desconectado';
            });
    }

    initSidebar();
    initGlobalSearch();
    initConfirmDialogs();
    initAutoDismissAlerts();
    initThemeToggle();
    initClock();
    initMongoStatus();
})();
