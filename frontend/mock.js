(function() {
    // Configuration
    let movingTargets = [];
    let animationInterval = null;
    let isRunning = false;
    
    // Callback when targets are detected/updated
    let onTargetsUpdateCallback = null;
    
    // Section Management
    let currentSection = 0;
    let sectionTimer = null;
    let sectionDurationMs = 0; // in milliseconds
    let sectionEndTime = null;
    
    // Target management
    let activeTargetCount = 0;
    let targetIdCounter = 0;
    
    // Radar boundaries (same as main radar)
    const RADAR_CENTER = { x: 350, y: 350 };
    const RADAR_RADIUS = 320;
    
    // New constant speed for targets (pixels per second)
    const TARGET_SPEED = 28; // Pixels per second (slow movement)
    
    // Pre-defined section configurations
    const SECTIONS = [
        { name: "Alpha", staticChance: 0.1, movingChance: 0.9, targetCount: { min: 3, max: 7 } },    // Mostly moving
        { name: "Bravo", staticChance: 0.8, movingChance: 0.2, targetCount: { min: 1, max: 4 } },    // Mostly static
        { name: "Charlie", staticChance: 0.5, movingChance: 0.5, targetCount: { min: 4, max: 9 } },  // Balanced
        { name: "Delta", staticChance: 0.2, movingChance: 0.8, targetCount: { min: 5, max: 10 } },   // Heavy moving
        { name: "Echo", staticChance: 0.95, movingChance: 0.05, targetCount: { min: 2, max: 5 } },   // Almost all static
        { name: "Foxtrot", staticChance: 0.3, movingChance: 0.7, targetCount: { min: 6, max: 12 } }, // High activity
        { name: "Golf", staticChance: 0.6, movingChance: 0.4, targetCount: { min: 3, max: 8 } },     // Mixed with more static
        { name: "Hotel", staticChance: 0.4, movingChance: 0.6, targetCount: { min: 4, max: 10 } },   // Mixed with more moving
        { name: "India", staticChance: 0.15, movingChance: 0.85, targetCount: { min: 7, max: 13 } }, // High moving count
        { name: "Juliett", staticChance: 0.85, movingChance: 0.15, targetCount: { min: 2, max: 6 } } // Mostly static
    ];
    
    // Get random section duration (in milliseconds) from 3 to 10 minutes (converted to ms)
    function getRandomSectionDuration() {
        const minutes = Math.floor(Math.random() * 8) + 3; // 3 to 10 minutes
        return minutes * 60 * 1000;
    }
    
    // Select a random section configuration
    function getRandomSection() {
        const randomIndex = Math.floor(Math.random() * SECTIONS.length);
        return { ...SECTIONS[randomIndex], index: randomIndex };
    }
    
    // Generate a static target (non-moving)
    function createStaticTarget(id) {
        const angle = Math.random() * 360;
        const distance = Math.random() * (RADAR_RADIUS - 20) + 10;
        const rad = angle * Math.PI / 180;
        const x = RADAR_CENTER.x + distance * Math.cos(rad);
        const y = RADAR_CENTER.y + distance * Math.sin(rad);
        
        return new MovingTarget(id, x, y, angle, distance, true); // static = true
    }
    
    // Target class
    class MovingTarget {
        constructor(id, x, y, angle, distance, isStatic = false) {
            this.id = id;
            this.x = x;
            this.y = y;
            this.angle = angle;
            this.distance = distance;
            this.isStatic = isStatic;
            
            if (isStatic) {
                this.speedX = 0;
                this.speedY = 0;
            } else {
                // Calculate a constant speed vector in a random direction
                const directionAngle = Math.random() * Math.PI * 2;
                this.speedX = Math.cos(directionAngle) * (TARGET_SPEED / 60); // Convert to per frame (60fps)
                this.speedY = Math.sin(directionAngle) * (TARGET_SPEED / 60);
            }
            
            this.lifeTime = 0;
            this.maxLifeTime = null; // Managed by section system, not individual target lifetime
            this.createdAt = Date.now();
            this.color = isStatic ? `hsl(0, 70%, 55%)` : `hsl(${Math.random() * 60 + 340}, 70%, 55%)`; // Red for static, red-magenta for moving
            this.size = isStatic ? 6 : 8;
        }
        
        update() {
            if (this.isStatic) return true; // Static targets don't move
            
            // Update position
            this.x += this.speedX;
            this.y += this.speedY;
            
            // Calculate new angle and distance
            const dx = this.x - RADAR_CENTER.x;
            const dy = this.y - RADAR_CENTER.y;
            this.distance = Math.sqrt(dx*dx + dy*dy);
            let angleRad = Math.atan2(dy, dx);
            this.angle = angleRad * 180 / Math.PI;
            if (this.angle < 0) this.angle += 360;
            
            // Bounce off radar boundaries
            if (this.distance >= RADAR_RADIUS - 5) {
                // Calculate reflection
                const normalX = dx / this.distance;
                const normalY = dy / this.distance;
                const dot = this.speedX * normalX + this.speedY * normalY;
                
                // Reflect velocity
                if (dot < 0) {
                    this.speedX -= 2 * dot * normalX;
                    this.speedY -= 2 * dot * normalY;
                    
                    // Push back inside boundary
                    const pushBack = (RADAR_RADIUS - 10 - this.distance) * 0.5;
                    this.x += normalX * pushBack;
                    this.y += normalY * pushBack;
                }
            }
            
            // Ensure target stays within canvas bounds (0-700)
            this.x = Math.min(Math.max(5, this.x), 695);
            this.y = Math.min(Math.max(5, this.y), 695);
            
            return true; // Always alive until section ends
        }
        
        draw(ctx) {
            ctx.save();
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, 2 * Math.PI);
            
            // Glow effect
            ctx.shadowBlur = 12;
            ctx.shadowColor = this.color;
            
            // Outer ring
            ctx.strokeStyle = this.color;
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Inner fill
            ctx.fillStyle = this.color;
            ctx.fill();
            
            // Inner core
            ctx.beginPath();
            ctx.arc(this.x, this.y, 3, 0, 2 * Math.PI);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            
            // Add ID label
            ctx.font = "10px 'Space Mono', monospace";
            ctx.fillStyle = '#ffffff';
            ctx.shadowBlur = 4;
            const prefix = this.isStatic ? 'S' : 'M';
            ctx.fillText(`${prefix}-${this.id}`, this.x + 8, this.y - 5);
            
            ctx.restore();
        }
        
        getTargetData() {
            return {
                id: this.id,
                x: Math.floor(this.x),
                y: Math.floor(this.y),
                angle: this.angle,
                distance: this.distance,
                timestamp: new Date().toLocaleTimeString(),
                type: this.isStatic ? 'STATIC' : 'MOVING'
            };
        }
    }
    
    // Generate random number of targets based on section configuration
    function getRandomTargetCountFromSection(section) {
        const { min, max } = section.targetCount;
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    
    // Create targets for a section based on its configuration
    function createTargetsForSection(section) {
        const targetCount = getRandomTargetCountFromSection(section);
        const newTargets = [];
        
        for (let i = 0; i < targetCount; i++) {
            targetIdCounter++;
            const isStatic = Math.random() < section.staticChance;
            
            if (isStatic) {
                newTargets.push(createStaticTarget(targetIdCounter));
            } else {
                // Create moving target at random position within radar
                const angle = Math.random() * 360;
                const distance = Math.random() * (RADAR_RADIUS - 30) + 20;
                const rad = angle * Math.PI / 180;
                const x = RADAR_CENTER.x + distance * Math.cos(rad);
                const y = RADAR_CENTER.y + distance * Math.sin(rad);
                newTargets.push(new MovingTarget(targetIdCounter, x, y, angle, distance, false));
            }
        }
        
        return newTargets;
    }
    
    // Start a new section
    function startNewSection() {
        // Clear existing targets
        if (movingTargets.length > 0) {
            // Notify about despawn of all current targets
            if (onTargetsUpdateCallback) {
                movingTargets.forEach(target => {
                    onTargetsUpdateCallback(target.getTargetData(), 'DESPAWN');
                });
            }
        }
        
        // Select new section
        const newSection = getRandomSection();
        currentSection = newSection.index;
        
        // Generate new targets for this section
        movingTargets = createTargetsForSection(newSection);
        activeTargetCount = movingTargets.length;
        
        // Notify about spawn of new targets
        if (onTargetsUpdateCallback) {
            movingTargets.forEach(target => {
                onTargetsUpdateCallback(target.getTargetData(), 'SPAWN');
            });
        }
        
        // Set new section duration
        sectionDurationMs = getRandomSectionDuration();
        sectionEndTime = Date.now() + sectionDurationMs;
        
        console.log(`🔄 New Section Started: ${newSection.name} | Duration: ${sectionDurationMs / 60000} min | Targets: ${activeTargetCount} (${movingTargets.filter(t => t.isStatic).length} static, ${movingTargets.filter(t => !t.isStatic).length} moving)`);
    }
    
    // Update all moving targets
    function updateTargets() {
        let needsSectionChange = false;
        
        // Check if current section has ended
        if (sectionEndTime && Date.now() >= sectionEndTime) {
            needsSectionChange = true;
        }
        
        if (needsSectionChange) {
            startNewSection();
        }
        
        // Update all targets
        movingTargets.forEach(target => {
            target.update();
        });
        
        // Trigger update callback for active targets
        if (onTargetsUpdateCallback) {
            movingTargets.forEach(target => {
                onTargetsUpdateCallback(target.getTargetData(), 'UPDATE');
            });
        }
    }
    
    // Draw all moving targets on radar
    function drawTargets(ctx) {
        movingTargets.forEach(target => {
            target.draw(ctx);
        });
    }
    
    // Get all current moving targets for detection
    function getCurrentTargets() {
        return movingTargets.map(target => target.getTargetData());
    }
    
    // Start the moving targets simulation
    function startMovingTargets(callback) {
        if (isRunning) return;
        
        onTargetsUpdateCallback = callback;
        isRunning = true;
        
        // Start the first section
        startNewSection();
        
        // Regular updates (60fps for smooth movement)
        animationInterval = setInterval(() => {
            if (!isRunning) return;
            updateTargets();
        }, 16); // ~60fps
    }
    
    // Stop the moving targets simulation
    function stopMovingTargets() {
        if (animationInterval) {
            clearInterval(animationInterval);
            animationInterval = null;
        }
        if (sectionTimer) {
            clearTimeout(sectionTimer);
            sectionTimer = null;
        }
        movingTargets = [];
        activeTargetCount = 0;
        isRunning = false;
        sectionEndTime = null;
        console.log('Moving targets simulation stopped');
    }
    
    // Check if simulation is running
    function isSimulationRunning() {
        return isRunning;
    }
    
    // Get active target count
    function getActiveTargetCount() {
        return activeTargetCount;
    }
    
    // Export functions for use in main radar
    window.MovingTargetSystem = {
        start: startMovingTargets,
        stop: stopMovingTargets,
        draw: drawTargets,
        getTargets: getCurrentTargets,
        isRunning: isSimulationRunning,
        getCount: getActiveTargetCount
    };
    
    console.log('Moving Target System initialized with section-based management and constant speed');
})();
