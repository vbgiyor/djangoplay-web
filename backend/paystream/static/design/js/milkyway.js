document.addEventListener('DOMContentLoaded', function () {
    const themeSwitch = document.getElementById('theme-switch');
    let starsContainer = document.getElementById('stars');
    let initialized = false;
    const sound = document.getElementById('toggle-sound');

    // Ensure stars container exists
    if (!starsContainer) {
        starsContainer = document.createElement('div');
        starsContainer.id = 'stars';
        document.body.prepend(starsContainer);
    }

    // Load saved theme
    const currentTheme = localStorage.getItem('theme') || 'default';
    if (currentTheme === 'space') {
        document.body.classList.add('space-theme');
        themeSwitch.checked = true;
        initSpaceTheme();

        // Try autoplay muted
        if (sound) {
            sound.currentTime = 0;
            sound.play().then(() => {
                setTimeout(() => {
                    sound.muted = false;
                }, 1000);
            }).catch(e => {
                console.warn("Autoplay blocked even muted:", e);
            });
        }
    }

    // Toggle event
    themeSwitch.addEventListener('change', function () {
        if (sound) {
            if (this.checked) {
                sound.currentTime = 0;
                sound.play().catch(e => console.warn("Sound play failed:", e));
            } else {
                sound.pause();
                sound.currentTime = 0;
            }
        }

        if (this.checked) {
            document.body.classList.add('space-theme');
            localStorage.setItem('theme', 'space');
            initSpaceTheme();
        } else {
            document.body.classList.remove('space-theme');
            localStorage.setItem('theme', 'default');
            starsContainer.innerHTML = '';
            initialized = false;
        }
    });

    function initSpaceTheme() {
        if (initialized) return;

        const numStars = 500; // Higher density for photo-like band
        const colors = [
            '#ffffff', '#ffffff', '#ffffff', '#ffffff', '#ffffff', // Mostly white
            'hsl(200, 20%, 90%)', // Blue
            'hsl(0, 20%, 90%)',   // Red
            'hsl(30, 20%, 90%)',  // Orange-yellow
            'hsl(120, 20%, 90%)'  // Added green
        ];

        function createStar() {
            const star = document.createElement('div');
            star.className = 'star';
            star.style.position = 'absolute';
            const size = Math.random() < 0.1 ? Math.random() * 3 + 3 : 2;
            star.style.width = `${size}px`;
            star.style.height = `${size}px`;
            star.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            star.style.borderRadius = '50%';

            // Diagonal clustering (bottom-left to top-right)
            const isMilkyWayStar = Math.random() < 0.75; // 75% in band
            if (isMilkyWayStar) {
                const x = Math.random() * 100;
                let y = 100 - x + (Math.random() * 30 - 15); // Diagonal with ±15% variation
                y = Math.max(0, Math.min(100, y));
                star.style.left = `${x}%`;
                star.style.top = `${y}%`;
                star.style.opacity = Math.random() * 0.7 + 0.3; // Brighter in band
            } else {
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.opacity = Math.random() * 0.5 + 0.1;
            }

            star.style.animation = `twinkle ${Math.random() * 3 + 2}s infinite ease-in-out, drift ${Math.random() * 20 + 10}s linear infinite`;
            starsContainer.appendChild(star);
        }

        function createShootingStar() {
            const shootingStar = document.createElement('div');
            shootingStar.className = 'shooting-star';
            shootingStar.style.position = 'absolute';
            shootingStar.style.width = '4px';
            shootingStar.style.height = '20px';
            // Photo-like trail with orange-purple tint
            shootingStar.style.background = 'linear-gradient(to bottom, rgba(255, 204, 153, 0.8), rgba(200, 150, 255, 0.4), transparent)';
            const x = Math.random() * 100;
            let y = 100 - x + (Math.random() * 30 - 15);
            y = Math.max(0, Math.min(100, y));
            shootingStar.style.left = `${x}%`;
            shootingStar.style.top = `${y}%`;
            shootingStar.style.animation = `streak ${Math.random() * 1 + 1}s linear`;
            starsContainer.appendChild(shootingStar);
            shootingStar.addEventListener('animationend', () => {
                shootingStar.remove();
            });
        }

        function createBrightStar() {
            const brightStar = document.createElement('div');
            brightStar.className = 'bright-star';
            brightStar.style.position = 'absolute';
            const size = 3;
            brightStar.style.width = `${size}px`;
            brightStar.style.height = `${size}px`;
            const brightColors = ['#00f', '#f00', '#ff0', '#0f0']; // Blue, red, yellow + green
            brightStar.style.backgroundColor = brightColors[Math.floor(Math.random() * brightColors.length)];
            brightStar.style.borderRadius = '50%';
            const x = Math.random() * 100;
            let y = 100 - x + (Math.random() * 30 - 15);
            y = Math.max(0, Math.min(100, y));
            brightStar.style.left = `${x}%`;
            brightStar.style.top = `${y}%`;
            brightStar.style.opacity = 1;
            brightStar.style.boxShadow = `0 0 8px 2px ${brightStar.style.backgroundColor}`;
            brightStar.style.animation = `bright-twinkle ${Math.random() * 2 + 1}s infinite ease-in-out`;
            starsContainer.appendChild(brightStar);
            setTimeout(() => {
                brightStar.remove();
            }, 3000);
        }

        function spawnBrightStar() {
            const numBrightStars = Math.floor(Math.random() * 2) + 2; // 2-3
            for (let i = 0; i < numBrightStars; i++) {
                setTimeout(createBrightStar, Math.random() * 1000);
            }
            setTimeout(spawnBrightStar, Math.random() * 4000 + 4000); // 4-8s
        }

        for (let i = 0; i < numStars; i++) {
            createStar();
        }

        function spawnShootingStar() {
            createShootingStar();
            setTimeout(spawnShootingStar, Math.random() * 10000 + 5000); // Periodic 5-15s
        }

        spawnShootingStar();
        spawnBrightStar();
        initialized = true;
    }
});