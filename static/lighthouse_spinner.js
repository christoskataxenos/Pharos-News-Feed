// 3D Volumetric Lighthouse Loading Spinner - Premium Version
let lighthouseActive = false;
let lighthouseRenderer, lighthouseScene, lighthouseCamera, lighthouseBeam, lighthouseAnimId;
let lighthouseGroup, seaMist;

function initLighthouse() {
    const canvas = document.getElementById('lighthouse-canvas');
    if (!canvas) return;

    // Αποφυγή επαναδημιουργίας αν υπάρχει ήδη ο renderer
    if (lighthouseRenderer) {
        return;
    }

    // Δημιουργία σκηνής & κάμερας για τον Φάρο
    lighthouseScene = new THREE.Scene();
    
    // Προσθήκη ομίχλης για ατμόσφαιρα
    lighthouseScene.fog = new THREE.FogExp2(0x05101a, 0.04);
    
    lighthouseCamera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    lighthouseCamera.position.set(0, 3, 10);

    lighthouseRenderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    lighthouseRenderer.setSize(200, 200);
    lighthouseRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Φωτισμός
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    lighthouseScene.add(ambientLight);

    // Φως Φάρου (Κίτρινο/Πορτοκαλί)
    const beaconLight = new THREE.PointLight(0xF4A261, 4, 15);
    beaconLight.position.set(0, 3.4, 0);
    lighthouseScene.add(beaconLight);

    // Κατευθυντικό φως για σκιές και βάθος
    const dirLight = new THREE.DirectionalLight(0x00B4D8, 1.5);
    dirLight.position.set(5, 8, 5);
    lighthouseScene.add(dirLight);

    // Ομαδοποίηση όλων των 3D στοιχείων του φάρου
    lighthouseGroup = new THREE.Group();

    // 1. Rocky Base (Βραχώδης νησίδα)
    const rockGeo = new THREE.IcosahedronGeometry(1.4, 1);
    const rockMat = new THREE.MeshStandardMaterial({ 
        color: 0x111e2e, 
        roughness: 0.9,
        metalness: 0.1,
        flatShading: true 
    });
    const rockMesh = new THREE.Mesh(rockGeo, rockMat);
    rockMesh.scale.set(1.4, 0.6, 1.4);
    rockMesh.position.y = -0.1;
    lighthouseGroup.add(rockMesh);

    // 2. Concrete Base Ring
    const baseRingGeo = new THREE.CylinderGeometry(0.9, 1.0, 0.4, 16);
    const baseRingMat = new THREE.MeshStandardMaterial({ 
        color: 0x334155, 
        roughness: 0.7 
    });
    const baseRingMesh = new THREE.Mesh(baseRingGeo, baseRingMat);
    baseRingMesh.position.y = 0.4;
    lighthouseGroup.add(baseRingMesh);

    // 3. Tapered Tower with Stripes
    const textureCanvas = document.createElement('canvas');
    textureCanvas.width = 128;
    textureCanvas.height = 128;
    const ctx = textureCanvas.getContext('2d');
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, 128, 128);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 32, 128, 32);
    ctx.fillRect(0, 96, 128, 32);

    const stripeTexture = new THREE.CanvasTexture(textureCanvas);
    stripeTexture.wrapS = THREE.RepeatWrapping;
    stripeTexture.wrapT = THREE.RepeatWrapping;
    stripeTexture.repeat.set(1, 1);

    const towerGeo = new THREE.CylinderGeometry(0.5, 0.8, 2.2, 16);
    const towerMat = new THREE.MeshStandardMaterial({ 
        map: stripeTexture,
        roughness: 0.6
    });
    const towerMesh = new THREE.Mesh(towerGeo, towerMat);
    towerMesh.position.y = 1.7;
    lighthouseGroup.add(towerMesh);

    // 4. Gallery / Balcony
    const balconyGeo = new THREE.CylinderGeometry(0.7, 0.7, 0.1, 16);
    const balconyMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.8 });
    const balconyMesh = new THREE.Mesh(balconyGeo, balconyMat);
    balconyMesh.position.y = 2.85;
    lighthouseGroup.add(balconyMesh);

    // 5. Metal Lantern Pillars
    const pillarMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.5 });
    const pillarCount = 6;
    for (let i = 0; i < pillarCount; i++) {
        const pillarGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.6, 6);
        const pillarMesh = new THREE.Mesh(pillarGeo, pillarMat);
        const angle = (i / pillarCount) * Math.PI * 2;
        pillarMesh.position.set(
            Math.cos(angle) * 0.45,
            3.2,
            Math.sin(angle) * 0.45
        );
        lighthouseGroup.add(pillarMesh);
    }

    // 6. Glowing Beacon Core
    const coreGeo = new THREE.SphereGeometry(0.18, 16, 16);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xffe3a8 });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.position.y = 3.2;
    lighthouseGroup.add(coreMesh);

    // 7. Cupola / Roof
    const roofGeo = new THREE.ConeGeometry(0.65, 0.5, 16);
    const roofMat = new THREE.MeshStandardMaterial({ 
        color: 0xef4444, 
        roughness: 0.4,
        metalness: 0.3
    });
    const roofMesh = new THREE.Mesh(roofGeo, roofMat);
    roofMesh.position.y = 3.75;
    lighthouseGroup.add(roofMesh);

    // 8. Volumetric Light Beam
    const beamCanvas = document.createElement('canvas');
    beamCanvas.width = 256;
    beamCanvas.height = 16;
    const beamCtx = beamCanvas.getContext('2d');
    const grad = beamCtx.createLinearGradient(0, 0, 256, 0);
    grad.addColorStop(0, 'rgba(244, 162, 97, 0.85)');
    grad.addColorStop(0.2, 'rgba(244, 162, 97, 0.4)');
    grad.addColorStop(1, 'rgba(244, 162, 97, 0.0)');

    const beamTexture = new THREE.CanvasTexture(beamCanvas);

    const beamGeo = new THREE.ConeGeometry(1.6, 9.0, 24, 1, true);
    beamGeo.translate(0, -4.5, 0);
    beamGeo.rotateX(Math.PI / 2);
    
    const beamMat = new THREE.MeshBasicMaterial({
        map: beamTexture,
        transparent: true,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
        depthWrite: false
    });
    
    lighthouseBeam = new THREE.Mesh(beamGeo, beamMat);
    lighthouseBeam.position.set(0, 3.2, 0);
    lighthouseGroup.add(lighthouseBeam);

    // Προσθήκη στη σκηνή
    lighthouseScene.add(lighthouseGroup);

    // 9. Sea Mist / Spray
    const mistCount = 60;
    const mistGeo = new THREE.BufferGeometry();
    const mistPositions = new Float32Array(mistCount * 3);

    for (let i = 0; i < mistCount; i++) {
        mistPositions[i * 3] = (Math.random() - 0.5) * 5;
        mistPositions[i * 3 + 1] = 0.2 + Math.random() * 3.5;
        mistPositions[i * 3 + 2] = (Math.random() - 0.5) * 5;
    }

    mistGeo.setAttribute('position', new THREE.BufferAttribute(mistPositions, 3));
    const mistMat = new THREE.PointsMaterial({
        color: 0x00B4D8,
        size: 0.1,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending
    });
    seaMist = new THREE.Points(mistGeo, mistMat);
    lighthouseScene.add(seaMist);
}

function animateLighthouse() {
    if (!lighthouseActive) return;
    lighthouseAnimId = requestAnimationFrame(animateLighthouse);

    const time = Date.now() * 0.001;

    // 1. Περιστροφή της Volumetric δέσμης φωτός
    if (lighthouseBeam) {
        lighthouseBeam.rotation.y += 0.04;
    }

    // 2. Ήπια κίνηση σωματιδίων αύρας
    if (seaMist) {
        const positions = seaMist.geometry.attributes.position.array;
        const count = positions.length / 3;
        for (let i = 0; i < count; i++) {
            positions[i * 3 + 1] += 0.005;
            positions[i * 3] += Math.sin(time + i) * 0.002;

            if (positions[i * 3 + 1] > 4.0) {
                positions[i * 3 + 1] = 0.2;
            }
        }
        seaMist.geometry.attributes.position.needsUpdate = true;
    }

    // 3. Δυναμική κίνηση κάμερας (Orbit & Float)
    if (lighthouseCamera) {
        const camRadius = 7.5;
        const camSpeed = time * 0.3;
        lighthouseCamera.position.x = Math.sin(camSpeed) * camRadius;
        lighthouseCamera.position.z = Math.cos(camSpeed) * camRadius;
        lighthouseCamera.position.y = 2.0 + Math.sin(time * 0.6) * 0.4;
        lighthouseCamera.lookAt(0, 2.6, 0);
    }

    if (lighthouseRenderer && lighthouseScene && lighthouseCamera) {
        lighthouseRenderer.render(lighthouseScene, lighthouseCamera);
    }
}

function startLighthouseAnimation() {
    if (!lighthouseRenderer) {
        initLighthouse();
    }
    lighthouseActive = true;
    animateLighthouse();
}

function stopLighthouseAnimation() {
    lighthouseActive = false;
    if (lighthouseAnimId) {
        cancelAnimationFrame(lighthouseAnimId);
    }
}

function showLighthouse() {
    const overlay = document.getElementById('lighthouse-loading');
    if (!overlay) return;
    overlay.classList.remove('hidden');
    overlay.style.display = 'flex';
    
    startLighthouseAnimation();
}

function hideLighthouse() {
    const overlay = document.getElementById('lighthouse-loading');
    if (overlay) {
        overlay.classList.add('hidden');
        overlay.style.display = 'none';
    }
    stopLighthouseAnimation();
}

// Εξαγωγή καθολικών συναρτήσεων
window.initLighthouse = initLighthouse;
window.startLighthouseAnimation = startLighthouseAnimation;
window.stopLighthouseAnimation = stopLighthouseAnimation;
window.showLighthouse = showLighthouse;
window.hideLighthouse = hideLighthouse;
