// Wait for Three.js to load
window.addEventListener('load', () => {
    if (typeof THREE === 'undefined') {
        console.error("Three.js didn't load.");
        return;
    }

    const canvas = document.getElementById('webgl-bg');
    if (!canvas) return;

    // Scene setup - Δημιουργία της σκηνής
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x05101a, 0.015); // Ομίχλη για βάθος
    
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 40;
    camera.position.y = 10;

    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Particle setup - Ρύθμιση σωματιδίων βιοφωταύγειας
    const particleCount = 1000;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const initialPositions = new Float32Array(particleCount * 3);
    const phases = new Float32Array(particleCount);
    const sizes = new Float32Array(particleCount);
    const speeds = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
        // Τυχαίες θέσεις στον τρισδιάστατο χώρο
        const x = (Math.random() - 0.5) * 120;
        const y = (Math.random() - 0.5) * 80;
        const z = (Math.random() - 0.5) * 80;
        
        positions[i * 3] = x;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = z;

        initialPositions[i * 3] = x;
        initialPositions[i * 3 + 1] = y;
        initialPositions[i * 3 + 2] = z;

        phases[i] = Math.random() * Math.PI * 2; // Φάση για το τρεμόπαιγμα του φωτός
        sizes[i] = 0.3 + Math.random() * 0.8; // Τυχαίο μέγεθος
        speeds[i] = 0.01 + Math.random() * 0.03; // Ταχύτητα ανόδου
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    // Custom Material για αυθεντικό glowing εφέ βιοφωταύγειας
    const material = new THREE.PointsMaterial({
        color: 0x00B4D8,
        size: 0.9,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // Interaction Variables - Μεταβλητές αλληλεπίδρασης
    let mouseX = 0;
    let mouseY = 0;
    let targetMouseX = 0;
    let targetMouseY = 0;
    const windowHalfX = window.innerWidth / 2;
    const windowHalfY = window.innerHeight / 2;

    // Ρίπλς από κλικ (Ripples)
    const ripples = [];
    const maxRippleRadius = 30;
    const rippleSpeed = 0.8;

    // Scroll tracking
    let scrollY = window.scrollY;
    let scrollSpeed = 0;
    let targetScrollSpeed = 0;

    // Event listeners
    document.addEventListener('mousemove', (event) => {
        targetMouseX = (event.clientX - windowHalfX);
        targetMouseY = (event.clientY - windowHalfY);
    });

    document.addEventListener('click', (event) => {
        // Μετατροπή των συντεταγμένων του κλικ σε 3D world space (κατά προσέγγιση στο z=0)
        const rect = renderer.domElement.getBoundingClientRect();
        const clickX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        const clickY = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        // Vector προβολής
        const vector = new THREE.Vector3(clickX, clickY, 0.5);
        vector.unproject(camera);
        const dir = vector.sub(camera.position).normalize();
        const distance = -camera.position.z / dir.z;
        const pos = camera.position.clone().add(dir.multiplyScalar(distance));

        // Προσθήκη νέου ripple
        ripples.push({
            x: pos.x,
            y: pos.y,
            z: pos.z,
            radius: 0.1,
            maxRadius: maxRippleRadius,
            force: 15.0
        });
    });

    window.addEventListener('scroll', () => {
        const currentScroll = window.scrollY;
        const diff = currentScroll - scrollY;
        targetScrollSpeed = diff * 0.15; // Επιτάχυνση ρευμάτων λόγω σκρολ
        scrollY = currentScroll;
    });

    // Handle Resize
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // Animation Loop
    const clock = new THREE.Clock();

    function animate() {
        requestAnimationFrame(animate);
        
        const time = clock.getElapsedTime();

        // Εξομάλυνση κίνησης ποντικιού και scroll speed
        mouseX += (targetMouseX - mouseX) * 0.05;
        mouseY += (targetMouseY - mouseY) * 0.05;
        scrollSpeed += (targetScrollSpeed - scrollSpeed) * 0.1;
        targetScrollSpeed *= 0.95; // Απόσβεση ταχύτητας scroll

        const positions = particles.geometry.attributes.position.array;

        // Ενημέρωση των κυμάτων ρίπλ (ripples)
        for (let r = ripples.length - 1; r >= 0; r--) {
            const ripple = ripples[r];
            ripple.radius += rippleSpeed;
            ripple.force *= 0.96; // Σταδιακή εξασθένιση της δύναμης

            if (ripple.radius > ripple.maxRadius || ripple.force < 0.1) {
                ripples.splice(r, 1);
            }
        }

        // Κίνηση των σωματιδίων
        for (let i = 0; i < particleCount; i++) {
            const idx = i * 3;
            
            // 1. Βασική ανοδική κίνηση (σαν φυσαλίδες/πλαγκτόν) + επίδραση scroll
            const currentSpeed = speeds[i] + Math.max(0, Math.abs(scrollSpeed) * 0.02);
            positions[idx + 1] += currentSpeed;

            // Επαναφορά στο κάτω μέρος αν βγει εκτός ορίων
            if (positions[idx + 1] > 40) {
                positions[idx + 1] = -40;
                positions[idx] = (Math.random() - 0.5) * 120;
            }

            // 2. Ήπιο οριζόντιο ρεύμα (wave motion)
            positions[idx] += Math.sin(time * 0.3 + phases[i]) * 0.015;

            // 3. Επίδραση από τα ripples (κύματα από κλικ)
            for (let r = 0; r < ripples.length; r++) {
                const ripple = ripples[r];
                const dx = positions[idx] - ripple.x;
                const dy = positions[idx + 1] - ripple.y;
                const dz = positions[idx + 2] - ripple.z;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

                // Αν το σωματίδιο είναι κοντά στο μέτωπο του κύματος
                if (dist > 0.1 && Math.abs(dist - ripple.radius) < 6) {
                    const pushForce = (1.0 - Math.abs(dist - ripple.radius) / 6) * ripple.force * 0.05;
                    positions[idx] += (dx / dist) * pushForce;
                    positions[idx + 1] += (dy / dist) * pushForce;
                    positions[idx + 2] += (dz / dist) * pushForce;
                }
            }

            // 4. Επαναφορά στην αρχική Z/X θέση σιγά σιγά για σταθερότητα
            const homeX = initialPositions[idx];
            positions[idx] += (homeX - positions[idx]) * 0.002;
        }
        
        particles.geometry.attributes.position.needsUpdate = true;

        // 5. Παράλλαξη κάμερας με βάση το ποντίκι
        const targetCamX = mouseX * 0.02;
        const targetCamY = 10 - (mouseY * 0.02);
        
        camera.position.x += (targetCamX - camera.position.x) * 0.05;
        camera.position.y += (targetCamY - camera.position.y) * 0.05;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    }

    animate();
});
