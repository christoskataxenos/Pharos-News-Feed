// Three.js 3D Stacks (Archipelago) Visualizer
// Handles the rendering of 3D wireframe meshes corresponding to news stacks.

(function() {
    let scene, camera, renderer, canvas;
    let meshes = {}; // Map of groupId -> ThreeJS Group
    let activeGroups = [];
    let hoveredGroupId = null;
    let animationFrameId = null;

    // Configuration for stacks
    const STACKS_CONFIG = {
        'dev-ops': {
            color: 0x00B4D8, // Bright Cyan
            geometry: function() { return new THREE.TorusKnotGeometry(0.5, 0.15, 64, 8); }
        },
        'science-tech': {
            color: 0x9d4edd, // Neon Purple
            geometry: function() { return new THREE.DodecahedronGeometry(0.6, 0); }
        },
        'media-podcasts': {
            color: 0xf4a261, // Warm Orange
            geometry: function() { return new THREE.OctahedronGeometry(0.6, 0); }
        },
        'general': {
            color: 0x2a9d8f, // Aegean Teal
            geometry: function() { return new THREE.IcosahedronGeometry(0.6, 1); }
        }
    };

    // Initialize 3D scene
    function init() {
        canvas = document.getElementById('stacks-3d-canvas');
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        
        scene = new THREE.Scene();
        
        // Perspective Camera suited for a wide, short canvas
        camera = new THREE.PerspectiveCamera(45, rect.width / rect.height, 0.1, 100);
        camera.position.z = 8;

        renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setSize(rect.width, rect.height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        // Soft ambient and point lights to make elements look holographic
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0x00B4D8, 1.5, 50);
        pointLight.position.set(0, 5, 5);
        scene.add(pointLight);

        // Raycasting for mouse interactions
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        const tooltip = document.getElementById('stacks-3d-tooltip');

        canvas.addEventListener('mousemove', (event) => {
            const rect = canvas.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(scene.children, true);

            let foundId = null;
            if (intersects.length > 0) {
                // Find parent object with userData containing stack groupId
                let obj = intersects[0].object;
                while (obj && !obj.userData.groupId) {
                    obj = obj.parent;
                }
                if (obj && obj.userData.groupId) {
                    foundId = obj.userData.groupId;
                }
            }

            if (foundId !== hoveredGroupId) {
                hoveredGroupId = foundId;
                highlightStack(foundId);

                // Update text helper on screen
                if (foundId && tooltip) {
                    const groupName = activeGroups[foundId] ? activeGroups[foundId].name : '';
                    tooltip.textContent = `# ${groupName} (click to view)`;
                    tooltip.style.color = '#00B4D8';
                    tooltip.style.opacity = '1.0';
                } else if (tooltip) {
                    tooltip.textContent = 'Select an Archipelago';
                    tooltip.style.color = 'var(--text-muted)';
                    tooltip.style.opacity = '0.8';
                }
            }
        });

        canvas.addEventListener('click', () => {
            if (hoveredGroupId && window.selectStackFrom3D) {
                // Pulse animation on click
                const clickedMesh = meshes[hoveredGroupId];
                if (clickedMesh) {
                    clickedMesh.scale.set(1.9, 1.9, 1.9);
                }
                window.selectStackFrom3D(hoveredGroupId);
            }
        });

        // Start animation loop
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        animate();
    }

    // Spacing configuration based on active stacks count
    function getXPosition(index, total) {
        if (total === 1) return 0;
        if (total === 2) return (index === 0) ? -1.8 : 1.8;
        if (total === 3) return (index - 1) * 2.2;
        // For 4 stacks
        return (index - 1.5) * 2.2;
    }

    // Called from app.js when categories are loaded
    window.initStacks3D = function(groups) {
        activeGroups = groups;
        
        // Wait for canvas to exist in DOM
        if (!scene) {
            init();
        }

        if (!scene) return;

        // Clear existing meshes
        Object.keys(meshes).forEach(key => {
            scene.remove(meshes[key]);
        });
        meshes = {};

        // Find active groups
        const activeIds = Object.keys(groups).filter(id => groups[id].categories.length > 0);
        
        activeIds.forEach((id, index) => {
            const config = STACKS_CONFIG[id];
            if (!config) return;

            const group = new THREE.Group();
            group.userData = { groupId: id };

            const geom = config.geometry();
            
            // 1. Semi-transparent inner solid mesh to give volume
            const solidMat = new THREE.MeshPhongMaterial({
                color: config.color,
                transparent: true,
                opacity: 0.1,
                shininess: 30
            });
            const solidMesh = new THREE.Mesh(geom, solidMat);
            group.add(solidMesh);

            // 2. Holographic outer wireframe mesh
            const wireMat = new THREE.MeshBasicMaterial({
                color: config.color,
                wireframe: true,
                transparent: true,
                opacity: 0.6
            });
            const wireMesh = new THREE.Mesh(geom, wireMat);
            group.add(wireMesh);

            // Position based on index
            group.position.x = getXPosition(index, activeIds.length);
            group.position.y = 0;
            group.position.z = 0;

            scene.add(group);
            meshes[id] = group;
        });
        
        // Handle resizing
        const resizeObserver = new ResizeObserver(() => {
            const rect = canvas.getBoundingClientRect();
            camera.aspect = rect.width / rect.height;
            camera.updateProjectionMatrix();
            renderer.setSize(rect.width, rect.height);
        });
        resizeObserver.observe(canvas);
    };

    // Public highlight trigger for when user hovers via HTML sidebar
    window.highlightStack3D = function(groupId) {
        hoveredGroupId = groupId;
        highlightStack(groupId);
        const tooltip = document.getElementById('stacks-3d-tooltip');
        if (groupId && tooltip && activeGroups[groupId]) {
            tooltip.textContent = `# ${activeGroups[groupId].name} (click to view)`;
            tooltip.style.color = '#00B4D8';
            tooltip.style.opacity = '1.0';
        } else if (tooltip) {
            tooltip.textContent = 'Select an Archipelago';
            tooltip.style.color = 'var(--text-muted)';
            tooltip.style.opacity = '0.8';
        }
    };

    // Set scale & rotation speeds
    function highlightStack(groupId) {
        Object.keys(meshes).forEach(key => {
            const m = meshes[key];
            if (key === groupId) {
                // Hovered stack
                m.userData.targetScale = 1.4;
                m.userData.targetRotationSpeed = 2.0;
                
                // Make wireframe glow brighter
                m.children[1].material.opacity = 1.0;
                m.children[0].material.opacity = 0.25;
            } else {
                // Others
                m.userData.targetScale = 1.0;
                m.userData.targetRotationSpeed = 0.5;
                m.children[1].material.opacity = 0.5;
                m.children[0].material.opacity = 0.08;
            }
        });
    }

    // Animation loop
    const clock = new THREE.Clock();

    function animate() {
        animationFrameId = requestAnimationFrame(animate);
        
        const time = clock.getElapsedTime();

        Object.keys(meshes).forEach((key, index) => {
            const m = meshes[key];
            const targetScale = m.userData.targetScale || 1.0;
            const targetSpeed = m.userData.targetRotationSpeed || 0.5;

            // Smooth interpolation (Lerp)
            m.scale.x += (targetScale - m.scale.x) * 0.1;
            m.scale.y += (targetScale - m.scale.y) * 0.1;
            m.scale.z += (targetScale - m.scale.z) * 0.1;

            // Rotate
            const speedX = 0.2 * targetSpeed;
            const speedY = 0.4 * targetSpeed;
            m.rotation.x += speedX * 0.05;
            m.rotation.y += speedY * 0.05;

            // Float up and down gently
            m.position.y = Math.sin(time * 1.5 + index * 1.2) * 0.15;
        });

        renderer.render(scene, camera);
    }

})();
