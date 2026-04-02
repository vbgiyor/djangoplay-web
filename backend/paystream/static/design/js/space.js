document.addEventListener('DOMContentLoaded', function () {
    const themeSwitch = document.getElementById('theme-switch');
    const starsContainer = document.getElementById('stars') || createStarsContainer();
    const sound = document.getElementById('toggle-sound');
    const music = document.getElementById('m-sound');  // 🔊 new: background music
    let initialized = false;

    function createStarsContainer() {
        const div = document.createElement('div');
        div.id = 'stars';
        document.body.prepend(div);
        return div;
    }

    // Load saved theme
    if (localStorage.getItem('theme') === 'space') {
        document.body.classList.add('space-theme');
        if (themeSwitch) {
            themeSwitch.checked = true;
        }
        initSpaceTheme();
        // 🔊 new: keep music playing on any page while space theme is enabled
        startMusic();
    }

    // Single event listener
    if (themeSwitch) {
        themeSwitch.addEventListener('change', function () {
            if (this.checked) {
                document.body.classList.add('space-theme');
                localStorage.setItem('theme', 'space');
                initSpaceTheme();
                playSound();      // existing: toggle sound
                startMusic();     // new: start / continue background music
                applyPulse();
                fixBugButton();
            } else {
                document.body.classList.remove('space-theme');
                localStorage.setItem('theme', 'default');
                starsContainer.innerHTML = '';
                initialized = false;
                stopSound();      // existing: stop toggle sound
                stopMusicLoop();  // new: stop background music
                resetBugButton();
            }
        });
    }

    function playSound() {
        if (sound) {
            sound.currentTime = 0;
            sound.play().catch(() => {});
        }
    }

    function stopSound() {
        if (sound) {
            sound.pause();
            sound.currentTime = 0;
        }
    }

    // 🔊 new: background music helpers
    function startMusic() {
        if (music) {
            if (music.paused) {
                music.volume = 0.05; // 5% volume (very low)
                music.currentTime = 0;
            }
            music.play().catch(() => {});
        }
    }

    function stopMusicLoop() {
        if (music) {
            music.pause();
            music.currentTime = 0;
        }
    }

    function applyPulse() {
        const btn = document.getElementById('bug-report-btn-footer') || document.getElementById('bug-report-btn');
        if (btn) {
            btn.style.animation = 'none';
            requestAnimationFrame(() => {
                btn.style.animation = '';
            });
        }
    }

    function fixBugButton() {
        const btn = document.getElementById('bug-report-btn-footer') || document.getElementById('bug-report-btn');
        if (btn) {
            btn.style.display = 'none';
            requestAnimationFrame(() => btn.style.display = '');
        }
    }

    function resetBugButton() {
        const btn = document.getElementById('bug-report-btn-footer') || document.getElementById('bug-report-btn');
        if (btn) btn.style.display = '';
    }

    function initSpaceTheme() {
        if (initialized) return;
        initialized = true;

        const numStars = 300;
        const colors = ['#ffffff', '#ffffff', '#ffffff', '#ffffff', 'hsl(200, 20%, 90%)', 'hsl(0, 20%, 90%)', 'hsl(30, 20%, 90%)'];

        function createStar() {
            const star = document.createElement('div');
            star.className = 'star';
            star.style.position = 'absolute';
            const size = Math.random() < 0.1 ? Math.random() * 3 + 3 : 2;
            star.style.width = star.style.height = `${size}px`;
            star.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            star.style.borderRadius = '50%';
            star.style.left = Math.random() * 100 + '%';
            star.style.top = Math.random() * 100 + '%';
            star.style.opacity = Math.random();
            star.style.animation = `twinkle ${Math.random() * 3 + 2}s infinite ease-in-out, drift ${Math.random() * 20 + 10}s linear infinite`;
            starsContainer.appendChild(star);
        }

        function createShootingStar() {
            const s = document.createElement('div');
            s.className = 'shooting-star';
            s.style.position = 'absolute';
            s.style.width = '4px';
            s.style.height = '20px';
            s.style.background = 'linear-gradient(to bottom, rgba(255,255,255,0.8), transparent)';
            s.style.left = Math.random() * 80 + 10 + '%';
            s.style.top = Math.random() * 50 + '%';
            s.style.animation = `streak ${Math.random() * 1 + 1}s linear`;
            starsContainer.appendChild(s);
            s.addEventListener('animationend', () => s.remove());
        }

        function createBrightStar() {
            const b = document.createElement('div');
            b.className = 'bright-star';
            const colors = ['#00f', '#f00', '#ff0'];
            b.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            b.style.width = b.style.height = '3px';
            b.style.borderRadius = '50%';
            b.style.position = 'absolute';
            b.style.left = Math.random() * 100 + '%';
            b.style.top = Math.random() * 100 + '%';
            b.style.boxShadow = `0 0 8px 2px ${b.style.backgroundColor}`;
            b.style.animation = `bright-twinkle ${Math.random() * 2 + 1}s infinite ease-in-out`;
            starsContainer.appendChild(b);
            setTimeout(() => b.remove(), 3000);
        }

        function spawnBrightStars() {
            for (let i = 0; i < 2 + Math.floor(Math.random() * 2); i++) {
                setTimeout(createBrightStar, Math.random() * 1000);
            }
            setTimeout(spawnBrightStars, Math.random() * 4000 + 4000);
        }

        for (let i = 0; i < numStars; i++) createStar();
        setTimeout(() => {
            createShootingStar();
            setTimeout(arguments.callee, Math.random() * 10000 + 5000);
        }, Math.random() * 5000);
        spawnBrightStars();
    }

    // Initial pulse
    setTimeout(applyPulse, 500);
});



// document.addEventListener('DOMContentLoaded', function () {
//     const themeSwitch = document.getElementById('theme-switch');
//     const starsContainer = document.getElementById('stars') || createStarsContainer();
//     const sound = document.getElementById('toggle-sound');
//     let initialized = false;

//     function createStarsContainer() {
//         const div = document.createElement('div');
//         div.id = 'stars';
//         document.body.prepend(div);
//         return div;
//     }

//     // Load saved theme
//     if (localStorage.getItem('theme') === 'space') {
//         document.body.classList.add('space-theme');
//         themeSwitch.checked = true;
//         initSpaceTheme();
//     }

//     // Single event listener
//     if (themeSwitch) {
//         themeSwitch.addEventListener('change', function () {
//             if (this.checked) {
//                 document.body.classList.add('space-theme');
//                 localStorage.setItem('theme', 'space');
//                 initSpaceTheme();
//                 playSound();
//                 applyPulse();
//                 fixBugButton();
//             } else {
//                 document.body.classList.remove('space-theme');
//                 localStorage.setItem('theme', 'default');
//                 starsContainer.innerHTML = '';
//                 initialized = false;
//                 stopSound();
//                 resetBugButton();
//             }
//         });
//     }

//     function playSound() {
//         if (sound) {
//             sound.currentTime = 0;
//             sound.play().catch(() => {});
//         }
//     }

//     function stopSound() {
//         if (sound) {
//             sound.pause();
//             sound.currentTime = 0;
//         }
//     }

//     function applyPulse() {
//         const btn = document.getElementById('bug-report-btn-footer') || document.getElementById('bug-report-btn');
//         if (btn) {
//             btn.style.animation = 'none';
//             requestAnimationFrame(() => {
//                 btn.style.animation = '';
//             });
//         }
//     }

//     function fixBugButton() {
//         const btn = document.getElementById('bug-report-btn-footer') || document.getElementById('bug-report-btn');
//         if (btn) {
//             btn.style.display = 'none';
//             requestAnimationFrame(() => btn.style.display = '');
//         }
//     }

//     function resetBugButton() {
//         const btn = document.getElementById('bug-report-btn-footer') || document.getElementById('bug-report-btn');
//         if (btn) btn.style.display = '';
//     }

//     function initSpaceTheme() {
//         if (initialized) return;
//         initialized = true;

//         const numStars = 300;
//         const colors = ['#ffffff', '#ffffff', '#ffffff', '#ffffff', 'hsl(200, 20%, 90%)', 'hsl(0, 20%, 90%)', 'hsl(30, 20%, 90%)'];

//         function createStar() {
//             const star = document.createElement('div');
//             star.className = 'star';
//             star.style.position = 'absolute';
//             const size = Math.random() < 0.1 ? Math.random() * 3 + 3 : 2;
//             star.style.width = star.style.height = `${size}px`;
//             star.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
//             star.style.borderRadius = '50%';
//             star.style.left = Math.random() * 100 + '%';
//             star.style.top = Math.random() * 100 + '%';
//             star.style.opacity = Math.random();
//             star.style.animation = `twinkle ${Math.random() * 3 + 2}s infinite ease-in-out, drift ${Math.random() * 20 + 10}s linear infinite`;
//             starsContainer.appendChild(star);
//         }

//         function createShootingStar() {
//             const s = document.createElement('div');
//             s.className = 'shooting-star';
//             s.style.position = 'absolute';
//             s.style.width = '4px';
//             s.style.height = '20px';
//             s.style.background = 'linear-gradient(to bottom, rgba(255,255,255,0.8), transparent)';
//             s.style.left = Math.random() * 80 + 10 + '%';
//             s.style.top = Math.random() * 50 + '%';
//             s.style.animation = `streak ${Math.random() * 1 + 1}s linear`;
//             starsContainer.appendChild(s);
//             s.addEventListener('animationend', () => s.remove());
//         }

//         function createBrightStar() {
//             const b = document.createElement('div');
//             b.className = 'bright-star';
//             const colors = ['#00f', '#f00', '#ff0'];
//             b.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
//             b.style.width = b.style.height = '3px';
//             b.style.borderRadius = '50%';
//             b.style.position = 'absolute';
//             b.style.left = Math.random() * 100 + '%';
//             b.style.top = Math.random() * 100 + '%';
//             b.style.boxShadow = `0 0 8px 2px ${b.style.backgroundColor}`;
//             b.style.animation = `bright-twinkle ${Math.random() * 2 + 1}s infinite ease-in-out`;
//             starsContainer.appendChild(b);
//             setTimeout(() => b.remove(), 3000);
//         }

//         function spawnBrightStars() {
//             for (let i = 0; i < 2 + Math.floor(Math.random() * 2); i++) {
//                 setTimeout(createBrightStar, Math.random() * 1000);
//             }
//             setTimeout(spawnBrightStars, Math.random() * 4000 + 4000);
//         }

//         for (let i = 0; i < numStars; i++) createStar();
//         setTimeout(() => {
//             createShootingStar();
//             setTimeout(arguments.callee, Math.random() * 10000 + 5000);
//         }, Math.random() * 5000);
//         spawnBrightStars();
//     }

//     // Initial pulse
//     setTimeout(applyPulse, 500);
// });