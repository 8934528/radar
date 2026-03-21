(function() {
    // ========== LOADER FUNCTIONALITY ==========
    const loaderOverlay = document.getElementById('loaderOverlay');
    const radarContent = document.getElementById('radarContent');
    const percentSpan = document.getElementById('loadingPercent');
    const loadingMsg = document.getElementById('loadingMessage');
    const dateTimeElement = document.getElementById('currentDateTime');
    
    let loaderAnimationFrameId = null;
    let loaderStartTime = null;
    let loaderIsComplete = false;
    
    // Random time selector between 3-10 seconds
    const timeOptions = [3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000];
    const DURATION_MS = timeOptions[Math.floor(Math.random() * timeOptions.length)];
    
    console.log(`%c[LOADER] Selected loading duration: ${DURATION_MS / 1000} seconds`, 'color: #0aff0a; font-family: monospace');
    
    const easeOutCubic = (t) => {
        return 1 - Math.pow(1 - t, 3);
    };
    
    const updateLoaderPercentage = (percent) => {
        if (percentSpan) {
            const intPercent = Math.min(100, Math.max(0, Math.floor(percent)));
            percentSpan.textContent = intPercent;
            
            if (intPercent === 100 && !loaderIsComplete) {
                loaderIsComplete = true;
                if (loaderAnimationFrameId) {
                    cancelAnimationFrame(loaderAnimationFrameId);
                    loaderAnimationFrameId = null;
                }
                console.log(`%c[+] LOADING COMPLETE: 100%% | System ready. (Duration: ${DURATION_MS / 1000} seconds)`, 'color: #0aff0a; font-weight: bold');
                if (loadingMsg) {
                    loadingMsg.style.borderRightColor = '#00ffaa';
                    loadingMsg.style.animation = 'none';
                }
                
                // Smooth transition to radar
                setTimeout(() => {
                    loaderOverlay.classList.add('fade-out');
                    setTimeout(() => {
                        loaderOverlay.style.display = 'none';
                        radarContent.style.display = 'block';
                        setTimeout(() => {
                            radarContent.classList.add('show');
                            // Initialize radar after transition
                            if (typeof initRadar === 'function') {
                                initRadar();
                            }
                        }, 50);
                    }, 800);
                }, 200);
            }
        }
    };
    
    const animateLoader = (timestamp) => {
        if (loaderIsComplete) return;
        
        if (!loaderStartTime) {
            loaderStartTime = timestamp;
        }
        
        const elapsed = timestamp - loaderStartTime;
        let progress = Math.min(1, elapsed / DURATION_MS);
        const easedProgress = easeOutCubic(progress);
        let percentValue = easedProgress * 100;
        
        if (progress >= 1.0) {
            percentValue = 100;
            updateLoaderPercentage(percentValue);
            if (loaderAnimationFrameId) {
                cancelAnimationFrame(loaderAnimationFrameId);
                loaderAnimationFrameId = null;
            }
            return;
        }
        
        updateLoaderPercentage(percentValue);
        
        if (!loaderIsComplete && percentValue < 100) {
            loaderAnimationFrameId = requestAnimationFrame(animateLoader);
        }
    };
    
    const startLoader = () => {
        if (loaderAnimationFrameId) {
            cancelAnimationFrame(loaderAnimationFrameId);
        }
        loaderIsComplete = false;
        loaderStartTime = null;
        updateLoaderPercentage(0);
        loaderAnimationFrameId = requestAnimationFrame(animateLoader);
        
        setTimeout(() => {
            if (!loaderIsComplete && percentSpan && parseInt(percentSpan.textContent) < 100) {
                if (parseInt(percentSpan.textContent) < 100) {
                    updateLoaderPercentage(100);
                    loaderIsComplete = true;
                    if (loaderAnimationFrameId) cancelAnimationFrame(loaderAnimationFrameId);
                }
            }
        }, DURATION_MS + 200);
    };
    
    const updateDateTime = () => {
        if (dateTimeElement) {
            const now = new Date();
            const options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            };
            const formattedDateTime = now.toLocaleString('en-ZA', options);
            dateTimeElement.textContent = formattedDateTime;
        }
    };
    
    updateDateTime();
    setInterval(updateDateTime, 1000);
    startLoader();
    
    // ========== RADAR FUNCTIONALITY ==========
    let radarInitialized = false;
    
    window.initRadar = function() {
        if (radarInitialized) return;
        radarInitialized = true;
        
        // DOM Elements
        const canvas = document.getElementById('radarCanvas');
        const ctx = canvas.getContext('2d');
        
        const cursorXSpan = document.getElementById('cursorX');
        const cursorYSpan = document.getElementById('cursorY');
        const cursorAngleSpan = document.getElementById('cursorAngle');
        const cursorDistSpan = document.getElementById('cursorDist');
        
        const clickXSpan = document.getElementById('clickX');
        const clickYSpan = document.getElementById('clickY');
        const clickAngleSpan = document.getElementById('clickAngle');
        const clickRadiusSpan = document.getElementById('clickRadius');
        
        const sweepAngleSpan = document.getElementById('sweepAngle');
        const rotSpeedSpan = document.getElementById('rotSpeed');
        
        const targetBadgeContainer = document.getElementById('targetBadgeContainer');
        const targetCountSpan = document.getElementById('targetCount');
        const targetCountBadge = document.getElementById('targetCountBadge');
        
        let radarCenter = { x: 350, y: 350 };
        let radarRadius = 320;
        let currentSweepAngle = 0;
        let animationId = null;
        let lastFrameTime = null;
        let sweepSpeed = 45;
        
        let showGridLines = true;
        let showBearingLines = true;
        let showCardinalLabels = true;
        let ringCount = 4;
        let bearingCount = 8;
        
        let mouseX = 0, mouseY = 0;
        let lastClickPoint = { x: null, y: null, angle: null, dist: null };
        
        let detectedTargets = [];
        let movingTargetsData = new Map();
        let targetIdCounter = 0;
        
        let securityModal, successModal, targetDetailsModal, settingsModal;
        let movingTargetSystem = null;
        let movingTargetsActive = false;
        
        // New variables for heat signature and mode
        let currentRadarMode = 'detection';
        let heatSignatureCanvas = null;
        let heatSignatureCtx = null;
        let heatSignatureData = [];
        let heatSignatureAnimation = null;
        
        // Security functions
        let devToolsOpen = false;
        let consoleAlertShown = false;

        // ========== HEAT SIGNATURE FUNCTIONS ==========
        let heatUpdateSpeed = 100; // ms
        let heatSmoothing = 5;
        let heatSensitivity = 1.0;
        let heatWaveformStyle = 'line';
        let peakIntensity = 0;
        
        function showSecurityAlert(message) {
            if (securityModal) {
                const modalBody = document.getElementById('securityModalBody');
                if (modalBody) modalBody.innerHTML = `<i class="bi bi-shield-exclamation"></i> ${message}<br><small class="text-muted">Access blocked for security reasons</small>`;
                securityModal.show();
            }
        }
        
        function showSuccessMessage(message) {
            if (successModal) {
                const modalBody = document.getElementById('successModalBody');
                if (modalBody) modalBody.innerHTML = `<i class="bi bi-check-circle"></i> ${message}`;
                successModal.show();
            }
        }
        
        function showTargetDetails() {
            if (targetDetailsModal && detectedTargets.length > 0) {
                const targetsListDiv = document.getElementById('targetsList');
                if (targetsListDiv) {
                    let targetsHtml = '<div class="table-responsive"><table class="table table-dark table-hover">';
                    targetsHtml += '<thead><tr><th>#</th><th>Target ID</th><th>Type</th><th>X (px)</th><th>Y (px)</th><th>Angle (°)</th><th>Distance (px)</th><th>Detection Time</th> </thead><tbody>';
                    
                    detectedTargets.forEach((target, index) => {
                        let targetTypeDisplay = '';
                        if (target.type === 'MOVING') {
                            targetTypeDisplay = '<span class="badge bg-warning">MOVING</span>';
                        } else if (target.type === 'STATIC') {
                            targetTypeDisplay = '<span class="badge bg-info">STATIC</span>';
                        } else {
                            targetTypeDisplay = '<span class="badge bg-danger">CLICK</span>';
                        }
                        
                        targetsHtml += `
                            <tr>
                                <td>${index + 1}</td>
                                <td><span class="badge bg-secondary">${target.id}</span></td>
                                <td>${targetTypeDisplay}</td>
                                <td>${target.x}</td>
                                <td>${target.y}</td>
                                <td>${target.angle.toFixed(1)}°</td>
                                <td>${target.distance.toFixed(1)}px</td>
                                <td>${target.timestamp}</td>
                            </tr>
                        `;
                    });
                    
                    targetsHtml += '</tbody></table></div>';
                    targetsHtml += `<div class="alert alert-info mt-3"><i class="bi bi-info-circle"></i> Total targets: ${detectedTargets.length} (${detectedTargets.filter(t => t.type === 'MOVING').length} moving, ${detectedTargets.filter(t => t.type === 'STATIC').length} static, ${detectedTargets.filter(t => t.type === 'CLICK').length} clicked)</div>`;
                    targetsListDiv.innerHTML = targetsHtml;
                }
                targetDetailsModal.show();
            }
        }
        
        function updateTargetBadge() {
            if (detectedTargets.length > 0) {
                targetBadgeContainer.style.display = 'inline-block';
                targetCountSpan.innerText = detectedTargets.length;
                const systemTargetCount = document.getElementById('systemTargetCount');
                if (systemTargetCount) systemTargetCount.innerText = detectedTargets.length;
            } else {
                targetBadgeContainer.style.display = 'none';
                const systemTargetCount = document.getElementById('systemTargetCount');
                if (systemTargetCount) systemTargetCount.innerText = '0';
            }
        }
        
        function addDetectedTarget(x, y, angle, distance, type = 'CLICK') {
            const isDuplicate = detectedTargets.some(target => {
                const dx = target.x - x;
                const dy = target.y - y;
                const dist = Math.sqrt(dx*dx + dy*dy);
                return dist < 15 && target.type === type;
            });
            
            if (!isDuplicate) {
                targetIdCounter++;
                const now = new Date();
                const timestamp = now.toLocaleTimeString();
                
                const newTarget = {
                    id: `TGT-${targetIdCounter}`,
                    x: Math.floor(x),
                    y: Math.floor(y),
                    angle: angle,
                    distance: distance,
                    timestamp: timestamp,
                    type: type,
                    createdAt: now
                };
                
                detectedTargets.push(newTarget);
                updateTargetBadge();
                
                if (detectedTargets.length > 100) detectedTargets.shift();
                return true;
            }
            return false;
        }
        
        function handleMovingTargetUpdate(targetData, eventType) {
            if (eventType === 'SPAWN') {
                addDetectedTarget(targetData.x, targetData.y, targetData.angle, targetData.distance, targetData.type);
                movingTargetsData.set(targetData.id, targetData);
            } else if (eventType === 'DESPAWN') {
                const index = detectedTargets.findIndex(t => t.id === targetData.id);
                if (index !== -1) {
                    detectedTargets.splice(index, 1);
                    updateTargetBadge();
                }
                movingTargetsData.delete(targetData.id);
            } else if (eventType === 'UPDATE') {
                movingTargetsData.set(targetData.id, targetData);
                const targetIndex = detectedTargets.findIndex(t => t.id === targetData.id);
                if (targetIndex !== -1) {
                    detectedTargets[targetIndex] = {
                        ...detectedTargets[targetIndex],
                        x: targetData.x,
                        y: targetData.y,
                        angle: targetData.angle,
                        distance: targetData.distance,
                        timestamp: new Date().toLocaleTimeString()
                    };
                }
            }
        }
        
        function drawMovingTargets() {
            if (movingTargetSystem && movingTargetSystem.isRunning()) {
                movingTargetSystem.draw(ctx);
            }
        }
        
        function drawDetectedTargets() {
            detectedTargets.forEach(target => {
                ctx.save();
                if (target.type === 'MOVING') {
                    ctx.beginPath();
                    ctx.arc(target.x, target.y, 7, 0, 2 * Math.PI);
                    ctx.fillStyle = '#ffaa44';
                    ctx.shadowBlur = 12;
                    ctx.shadowColor = '#ff8800';
                    ctx.fill();
                    ctx.beginPath();
                    ctx.arc(target.x, target.y, 3, 0, 2 * Math.PI);
                    ctx.fillStyle = '#ffffff';
                    ctx.fill();
                } else if (target.type === 'STATIC') {
                    ctx.beginPath();
                    ctx.arc(target.x, target.y, 6, 0, 2 * Math.PI);
                    ctx.fillStyle = '#66ccff';
                    ctx.shadowBlur = 8;
                    ctx.shadowColor = '#3399ff';
                    ctx.fill();
                    ctx.beginPath();
                    ctx.arc(target.x, target.y, 2, 0, 2 * Math.PI);
                    ctx.fillStyle = '#ffffff';
                    ctx.fill();
                } else {
                    ctx.beginPath();
                    ctx.arc(target.x, target.y, 6, 0, 2 * Math.PI);
                    ctx.fillStyle = '#ff4444';
                    ctx.shadowBlur = 12;
                    ctx.shadowColor = '#ff0000';
                    ctx.fill();
                    ctx.beginPath();
                    ctx.arc(target.x, target.y, 3, 0, 2 * Math.PI);
                    ctx.fillStyle = '#ffffff';
                    ctx.fill();
                }
                ctx.font = "10px 'Space Mono', monospace";
                ctx.fillStyle = target.type === 'MOVING' ? '#ffaa88' : (target.type === 'STATIC' ? '#88aaff' : '#ff8888');
                ctx.shadowBlur = 4;
                ctx.fillText(target.id, target.x + 8, target.y - 5);
                ctx.restore();
            });
        }
        
        function drawStaticGrid() {
            ctx.save();
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = '#1faa6a';
            ctx.fillStyle = '#00ff9d';
            ctx.lineWidth = 1.5;
            ctx.shadowBlur = 0;
            
            if (showGridLines) {
                for (let i = 1; i <= ringCount; i++) {
                    const radius = radarRadius * (i / ringCount);
                    ctx.beginPath();
                    ctx.arc(radarCenter.x, radarCenter.y, radius, 0, Math.PI * 2);
                    ctx.strokeStyle = '#2b7a4b';
                    ctx.setLineDash([5, 8]);
                    ctx.stroke();
                }
            }
            
            ctx.setLineDash([]);
            ctx.lineWidth = 1;
            
            if (showBearingLines) {
                for (let i = 0; i < bearingCount; i++) {
                    const angleDeg = i * (360 / bearingCount);
                    const angleRad = angleDeg * Math.PI / 180;
                    const x2 = radarCenter.x + radarRadius * Math.cos(angleRad);
                    const y2 = radarCenter.y + radarRadius * Math.sin(angleRad);
                    ctx.beginPath();
                    ctx.moveTo(radarCenter.x, radarCenter.y);
                    ctx.lineTo(x2, y2);
                    ctx.strokeStyle = '#2b8f60';
                    ctx.stroke();
                }
            }
            
            ctx.beginPath();
            ctx.arc(radarCenter.x, radarCenter.y, radarRadius, 0, Math.PI * 2);
            ctx.strokeStyle = '#00ff9d';
            ctx.lineWidth = 2;
            ctx.setLineDash([]);
            ctx.stroke();
            
            ctx.beginPath();
            ctx.arc(radarCenter.x, radarCenter.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = '#00ff9d';
            ctx.fill();
            
            ctx.beginPath();
            ctx.moveTo(radarCenter.x - 12, radarCenter.y);
            ctx.lineTo(radarCenter.x + 12, radarCenter.y);
            ctx.moveTo(radarCenter.x, radarCenter.y - 12);
            ctx.lineTo(radarCenter.x, radarCenter.y + 12);
            ctx.strokeStyle = '#b3ffcf';
            ctx.lineWidth = 1.5;
            ctx.stroke();
            
            if (showCardinalLabels) {
                ctx.font = "12px 'Space Mono', monospace";
                ctx.fillStyle = '#6fbf8a';
                ctx.shadowBlur = 0;
                ctx.fillText("N", radarCenter.x - 7, radarCenter.y - radarRadius + 10);
                ctx.fillText("E", radarCenter.x + radarRadius - 15, radarCenter.y + 5);
                ctx.fillText("S", radarCenter.x - 5, radarCenter.y + radarRadius - 6);
                ctx.fillText("W", radarCenter.x - radarRadius + 8, radarCenter.y + 5);
            }
            ctx.restore();
        }
        
        function drawSweep(angleDeg) {
            ctx.save();
            const angleRad = angleDeg * Math.PI / 180;
            const endX = radarCenter.x + radarRadius * Math.cos(angleRad);
            const endY = radarCenter.y + radarRadius * Math.sin(angleRad);
            
            const gradient = ctx.createLinearGradient(radarCenter.x, radarCenter.y, endX, endY);
            gradient.addColorStop(0, '#00ff9d');
            gradient.addColorStop(0.6, '#00cc7a');
            gradient.addColorStop(1, 'rgba(0, 255, 100, 0)');
            ctx.beginPath();
            ctx.moveTo(radarCenter.x, radarCenter.y);
            ctx.lineTo(endX, endY);
            ctx.lineWidth = 4;
            ctx.strokeStyle = gradient;
            ctx.shadowBlur = 8;
            ctx.shadowColor = '#00ff9d';
            ctx.stroke();
            
            ctx.beginPath();
            ctx.arc(endX, endY, 3, 0, 2 * Math.PI);
            ctx.fillStyle = '#b3ffcf';
            ctx.shadowBlur = 10;
            ctx.fill();
            
            ctx.beginPath();
            ctx.moveTo(radarCenter.x, radarCenter.y);
            ctx.lineTo(endX, endY);
            ctx.lineWidth = 1.2;
            ctx.strokeStyle = '#ffffffcc';
            ctx.stroke();
            ctx.restore();
        }
        
        function drawClickMarker() {
            if (lastClickPoint.x !== null && lastClickPoint.x >= 0 && lastClickPoint.x <= canvas.width &&
                lastClickPoint.y !== null && lastClickPoint.y >= 0 && lastClickPoint.y <= canvas.height) {
                ctx.save();
                ctx.beginPath();
                ctx.arc(lastClickPoint.x, lastClickPoint.y, 8, 0, 2 * Math.PI);
                ctx.strokeStyle = '#ffaa44';
                ctx.lineWidth = 2.5;
                ctx.setLineDash([4, 4]);
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(lastClickPoint.x, lastClickPoint.y, 3, 0, 2 * Math.PI);
                ctx.fillStyle = '#ffcc55';
                ctx.shadowBlur = 6;
                ctx.fill();
                ctx.setLineDash([]);
                ctx.beginPath();
                ctx.moveTo(lastClickPoint.x - 12, lastClickPoint.y);
                ctx.lineTo(lastClickPoint.x + 12, lastClickPoint.y);
                ctx.moveTo(lastClickPoint.x, lastClickPoint.y - 12);
                ctx.lineTo(lastClickPoint.x, lastClickPoint.y + 12);
                ctx.strokeStyle = '#ffaa66';
                ctx.lineWidth = 1.2;
                ctx.stroke();
                ctx.restore();
            }
        }
        
        function renderFrame() {
            drawStaticGrid();
            drawSweep(currentSweepAngle);
            drawMovingTargets();
            drawDetectedTargets();
            drawClickMarker();
            sweepAngleSpan.innerText = currentSweepAngle.toFixed(1) + "°";
        }
        
        function animateRadar(now) {
            if (!lastFrameTime) {
                lastFrameTime = now;
                requestAnimationFrame(animateRadar);
                return;
            }
            let delta = Math.min(0.05, (now - lastFrameTime) / 1000);
            if (delta > 0) {
                currentSweepAngle += sweepSpeed * delta;
                if (currentSweepAngle >= 360) currentSweepAngle -= 360;
                renderFrame();
            }
            lastFrameTime = now;
            animationId = requestAnimationFrame(animateRadar);
        }
        
        function getPolarCoordinates(px, py) {
            const dx = px - radarCenter.x;
            const dy = py - radarCenter.y;
            const distance = Math.sqrt(dx*dx + dy*dy);
            let angleRad = Math.atan2(dy, dx);
            let angleDeg = angleRad * 180 / Math.PI;
            if (angleDeg < 0) angleDeg += 360;
            return { angle: angleDeg, distance: distance, dx, dy };
        }
        
        function updateMouseCoordinateDisplay() {
            if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            
            let canvasX = (mouseX - rect.left) * scaleX;
            let canvasY = (mouseY - rect.top) * scaleY;
            canvasX = Math.min(Math.max(0, canvasX), canvas.width);
            canvasY = Math.min(Math.max(0, canvasY), canvas.height);
            
            cursorXSpan.innerText = Math.floor(canvasX);
            cursorYSpan.innerText = Math.floor(canvasY);
            
            const polar = getPolarCoordinates(canvasX, canvasY);
            cursorAngleSpan.innerText = polar.angle.toFixed(1) + "°";
            cursorDistSpan.innerText = polar.distance.toFixed(1);
        }
        
        function updateClickDisplay(clickCanvasX, clickCanvasY) {
            const polar = getPolarCoordinates(clickCanvasX, clickCanvasY);
            lastClickPoint = { x: clickCanvasX, y: clickCanvasY, angle: polar.angle, dist: polar.distance };
            clickXSpan.innerText = Math.floor(clickCanvasX);
            clickYSpan.innerText = Math.floor(clickCanvasY);
            clickAngleSpan.innerText = polar.angle.toFixed(1) + "°";
            clickRadiusSpan.innerText = polar.distance.toFixed(1);
            
            if (polar.distance <= radarRadius) {
                addDetectedTarget(clickCanvasX, clickCanvasY, polar.angle, polar.distance, 'CLICK');
            }
            renderFrame();
        }
        
        function onCanvasMouseMove(e) {
            const rect = canvas.getBoundingClientRect();
            mouseX = e.clientX;
            mouseY = e.clientY;
            if (mouseX >= rect.left && mouseX <= rect.right && mouseY >= rect.top && mouseY <= rect.bottom) {
                updateMouseCoordinateDisplay();
            } else {
                cursorXSpan.innerText = "---";
                cursorYSpan.innerText = "---";
                cursorAngleSpan.innerText = "---";
                cursorDistSpan.innerText = "---";
            }
        }
        
        function onCanvasClick(e) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            let clickCanvasX = (e.clientX - rect.left) * scaleX;
            let clickCanvasY = (e.clientY - rect.top) * scaleY;
            clickCanvasX = Math.min(Math.max(0, clickCanvasX), canvas.width);
            clickCanvasY = Math.min(Math.max(0, clickCanvasY), canvas.height);
            updateClickDisplay(clickCanvasX, clickCanvasY);
        }
        
        function handleResize() {
            canvas.width = 700;
            canvas.height = 700;
            radarRadius = 320;
            radarCenter = { x: canvas.width/2, y: canvas.height/2 };
            renderFrame();
        }
        
        // ========== HEAT SIGNATURE FUNCTIONS ==========
        function initHeatSignature() {
            heatSignatureCanvas = document.getElementById('heatSignatureCanvas');
            if (heatSignatureCanvas) {

                heatSignatureCanvas.width = 1000;
                heatSignatureCanvas.height = 180;
                heatSignatureCtx = heatSignatureCanvas.getContext('2d');

                for (let i = 0; i < 200; i++) {
                    heatSignatureData.push(0.2);
                }
                drawHeatSignature();
                startHeatSignatureAnimation();
            }
        }

        function smoothData(data, windowSize) {
            const result = [];
            for (let i = 0; i < data.length; i++) {
                let sum = 0;
                let count = 0;
                for (let j = Math.max(0, i - windowSize); j <= Math.min(data.length - 1, i + windowSize); j++) {
                    sum += data[j];
                    count++;
                }
                result.push(sum / count);
            }
            return result;
        }
        
        function drawHeatSignature() {
            if (!heatSignatureCtx || !heatSignatureCanvas) return;
            
            const width = heatSignatureCanvas.width;
            const height = heatSignatureCanvas.height;
            const dataLength = heatSignatureData.length;
            
            // Apply smoothing
            let displayData = heatSmoothing > 1 ? smoothData(heatSignatureData, Math.floor(heatSmoothing)) : [...heatSignatureData];
            
            heatSignatureCtx.clearRect(0, 0, width, height);
            
            // Draw background grid
            heatSignatureCtx.beginPath();
            heatSignatureCtx.strokeStyle = '#1f322a';
            heatSignatureCtx.lineWidth = 0.5;
            heatSignatureCtx.setLineDash([2, 4]);
            for (let i = 0; i <= 4; i++) {
                const y = height - (i * height / 4);
                heatSignatureCtx.beginPath();
                heatSignatureCtx.moveTo(0, y);
                heatSignatureCtx.lineTo(width, y);
                heatSignatureCtx.stroke();
            }
            heatSignatureCtx.setLineDash([]);
            
            if (heatWaveformStyle === 'bars') {
                // Bar chart style
                const barWidth = width / displayData.length;
                for (let i = 0; i < displayData.length; i++) {
                    const intensity = Math.min(1, Math.max(0, displayData[i] * heatSensitivity));
                    const barHeight = intensity * (height - 30);
                    const x = i * barWidth;
                    const y = height - barHeight - 15;
                    
                    let color;
                    if (intensity < 0.33) color = '#3a86ff';
                    else if (intensity < 0.66) color = '#ffaa44';
                    else color = '#ff4444';
                    
                    heatSignatureCtx.fillStyle = color;
                    heatSignatureCtx.fillRect(x, y, barWidth - 1, barHeight);
                    
                    // Add gradient effect
                    const gradient = heatSignatureCtx.createLinearGradient(x, y, x + barWidth, y + barHeight);
                    gradient.addColorStop(0, color);
                    gradient.addColorStop(1, 'rgba(255,255,255,0.3)');
                    heatSignatureCtx.fillStyle = gradient;
                    heatSignatureCtx.fillRect(x, y, barWidth - 1, barHeight);
                }
            } else if (heatWaveformStyle === 'line') {
                // Smooth line style
                heatSignatureCtx.beginPath();
                heatSignatureCtx.strokeStyle = '#00ff9d';
                heatSignatureCtx.lineWidth = 2.5;
                heatSignatureCtx.shadowBlur = 4;
                heatSignatureCtx.shadowColor = '#00ff9d';
                
                const step = width / (displayData.length - 1);
                for (let i = 0; i < displayData.length; i++) {
                    const intensity = Math.min(1, Math.max(0, displayData[i] * heatSensitivity));
                    const x = i * step;
                    const y = height - (intensity * (height - 30)) - 15;
                    
                    if (i === 0) {
                        heatSignatureCtx.moveTo(x, y);
                    } else {
                        heatSignatureCtx.lineTo(x, y);
                    }
                }
                heatSignatureCtx.stroke();
                
                // Add gradient fill under line
                if (heatWaveformStyle === 'area') {
                    heatSignatureCtx.lineTo(width, height - 15);
                    heatSignatureCtx.lineTo(0, height - 15);
                    heatSignatureCtx.closePath();
                    const gradient = heatSignatureCtx.createLinearGradient(0, 0, 0, height);
                    gradient.addColorStop(0, 'rgba(0, 255, 157, 0.4)');
                    gradient.addColorStop(1, 'rgba(0, 255, 157, 0.05)');
                    heatSignatureCtx.fillStyle = gradient;
                    heatSignatureCtx.fill();
                }
                
                // Add points
                heatSignatureCtx.fillStyle = '#00ff9d';
                for (let i = 0; i < displayData.length; i += Math.max(1, Math.floor(displayData.length / 20))) {
                    const intensity = Math.min(1, Math.max(0, displayData[i] * heatSensitivity));
                    const x = i * step;
                    const y = height - (intensity * (height - 30)) - 15;
                    heatSignatureCtx.beginPath();
                    heatSignatureCtx.arc(x, y, 2, 0, 2 * Math.PI);
                    heatSignatureCtx.fill();
                }
            } else {
                // Area fill style
                heatSignatureCtx.beginPath();
                for (let i = 0; i < displayData.length; i++) {
                    const intensity = Math.min(1, Math.max(0, displayData[i] * heatSensitivity));
                    const x = (i / (displayData.length - 1)) * width;
                    const y = height - (intensity * (height - 30)) - 15;
                    
                    if (i === 0) {
                        heatSignatureCtx.moveTo(x, y);
                    } else {
                        heatSignatureCtx.lineTo(x, y);
                    }
                }
                heatSignatureCtx.lineTo(width, height - 15);
                heatSignatureCtx.lineTo(0, height - 15);
                heatSignatureCtx.closePath();
                
                const gradient = heatSignatureCtx.createLinearGradient(0, 0, 0, height);
                gradient.addColorStop(0, 'rgba(0, 255, 157, 0.6)');
                gradient.addColorStop(0.5, 'rgba(255, 170, 68, 0.3)');
                gradient.addColorStop(1, 'rgba(255, 68, 68, 0.1)');
                heatSignatureCtx.fillStyle = gradient;
                heatSignatureCtx.fill();
                
                heatSignatureCtx.beginPath();
                heatSignatureCtx.strokeStyle = '#00ff9d';
                heatSignatureCtx.lineWidth = 2;
                for (let i = 0; i < displayData.length; i++) {
                    const intensity = Math.min(1, Math.max(0, displayData[i] * heatSensitivity));
                    const x = (i / (displayData.length - 1)) * width;
                    const y = height - (intensity * (height - 30)) - 15;
                    
                    if (i === 0) {
                        heatSignatureCtx.moveTo(x, y);
                    } else {
                        heatSignatureCtx.lineTo(x, y);
                    }
                }
                heatSignatureCtx.stroke();
            }
            
            heatSignatureCtx.shadowBlur = 0;
            
            // Draw baseline
            heatSignatureCtx.beginPath();
            heatSignatureCtx.strokeStyle = '#2b7a4b';
            heatSignatureCtx.lineWidth = 1;
            heatSignatureCtx.setLineDash([5, 5]);
            heatSignatureCtx.moveTo(0, height - 15);
            heatSignatureCtx.lineTo(width, height - 15);
            heatSignatureCtx.stroke();
            heatSignatureCtx.setLineDash([]);
        }
        
        function updateHeatSignature() {
            // Calculate heat based on detected targets and their movement
            let totalIntensity = 0;
            let targetCount = detectedTargets.length;
            
            detectedTargets.forEach(target => {
                if (target.type === 'MOVING') {
                    totalIntensity += 0.8;
                } else if (target.type === 'STATIC') {
                    totalIntensity += 0.3;
                } else {
                    totalIntensity += 0.5;
                }
            });
            
            // Normalize intensity based on target count
            let intensity = Math.min(1, totalIntensity / 12);
            
            // Add noise based on sweep angle
            const sweepEffect = Math.sin(currentSweepAngle * Math.PI / 180) * 0.08;
            intensity = Math.min(1, Math.max(0, intensity + sweepEffect));
            
            // Apply sensitivity
            intensity = Math.min(1, intensity * heatSensitivity);
            
            // Update peak
            if (intensity > peakIntensity) {
                peakIntensity = intensity;
                const peakSpan = document.getElementById('peakSignatureLevel');
                if (peakSpan) peakSpan.innerText = Math.floor(peakIntensity * 100) + '%';
            }
            
            // Decay peak slowly
            peakIntensity = Math.max(peakIntensity * 0.998, intensity);
            
            // Update signature level display
            const signatureSpan = document.getElementById('currentSignatureLevel');
            if (signatureSpan) {
                if (intensity < 0.25) signatureSpan.textContent = 'Nominal';
                else if (intensity < 0.5) signatureSpan.textContent = 'Elevated';
                else if (intensity < 0.75) signatureSpan.textContent = 'High';
                else signatureSpan.textContent = 'CRITICAL';
                
                signatureSpan.className = intensity > 0.6 ? 'text-danger' : (intensity > 0.3 ? 'text-warning' : 'text-success');
            }
            
            // Add new data point
            heatSignatureData.push(intensity);
            if (heatSignatureData.length > 200) heatSignatureData.shift();
            
            drawHeatSignature();
        }
        
        function startHeatSignatureAnimation() {
            if (heatSignatureAnimation) clearInterval(heatSignatureAnimation);
            heatSignatureAnimation = setInterval(() => {
                updateHeatSignature();
            }, heatUpdateSpeed);
        }

        function initHeatSignatureControls() {
            const heatSpeedSlider = document.getElementById('heatSpeedSlider');
            const heatSpeedValue = document.getElementById('heatSpeedValue');
            const smoothingSlider = document.getElementById('smoothingSlider');
            const smoothingValue = document.getElementById('smoothingValue');
            const sensitivitySlider = document.getElementById('sensitivitySlider');
            const sensitivityValue = document.getElementById('sensitivityValue');
            const waveformSelect = document.getElementById('waveformStyle');
            
            if (heatSpeedSlider) {
                heatSpeedSlider.addEventListener('input', (e) => {
                    heatUpdateSpeed = parseInt(e.target.value);
                    heatSpeedValue.innerText = heatUpdateSpeed;
                    startHeatSignatureAnimation();
                });
            }
            
            if (smoothingSlider) {
                smoothingSlider.addEventListener('input', (e) => {
                    heatSmoothing = parseInt(e.target.value);
                    smoothingValue.innerText = heatSmoothing;
                    drawHeatSignature();
                });
            }
            
            if (sensitivitySlider) {
                sensitivitySlider.addEventListener('input', (e) => {
                    heatSensitivity = parseFloat(e.target.value);
                    sensitivityValue.innerText = heatSensitivity.toFixed(1);
                    drawHeatSignature();
                });
            }
            
            if (waveformSelect) {
                waveformSelect.addEventListener('change', (e) => {
                    heatWaveformStyle = e.target.value;
                    drawHeatSignature();
                });
            }
        }

        function blockDevToolsDuringLoader() {
            const blockHandler = (e) => {
                if (loaderOverlay && loaderOverlay.style.display !== 'none') {
                    e.preventDefault();
                    return false;
                }
                return true;
            };
            
            document.addEventListener('keydown', function(e) {
                if (loaderOverlay && loaderOverlay.style.display !== 'none') {
                    if (e.key === 'F12' || 
                        (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J' || e.key === 'C')) ||
                        (e.ctrlKey && e.key === 'u')) {
                        e.preventDefault();
                        console.clear();
                        return false;
                    }
                }
            });
            
            document.addEventListener('contextmenu', function(e) {
                if (loaderOverlay && loaderOverlay.style.display !== 'none') {
                    e.preventDefault();
                    return false;
                }
            });
        }

        blockDevToolsDuringLoader();
        
        // ========== FULLSCREEN FUNCTION ==========
        function initFullscreenButton() {
            const fullscreenBtn = document.getElementById('fullscreenBtn');
            const radarCard = document.querySelector('.radar-card');
            
            if (fullscreenBtn) {
                fullscreenBtn.addEventListener('click', () => {
                    if (!document.fullscreenElement) {
                        radarCard.requestFullscreen().catch(err => {
                            console.error(`Error attempting to enable fullscreen: ${err.message}`);
                        });
                    } else {
                        document.exitFullscreen();
                    }
                });
                
                // Update button icon when fullscreen changes
                document.addEventListener('fullscreenchange', () => {
                    if (document.fullscreenElement) {
                        fullscreenBtn.innerHTML = '<i class="bi bi-fullscreen-exit"></i>';
                        fullscreenBtn.title = 'Exit Full Screen';
                    } else {
                        fullscreenBtn.innerHTML = '<i class="bi bi-arrows-fullscreen"></i>';
                        fullscreenBtn.title = 'Full Screen Mode';
                    }
                });
            }
        }
        
        // ========== RADAR MODE DROPDOWN FUNCTION ==========
        function initRadarModeDropdown() {
            const dropdownItems = document.querySelectorAll('[data-mode]');
            const modeNames = {
                adas: 'Automotive ADAS',
                mining: 'Mining Monitoring',
                wifi: 'Wi-Fi Scanning'
            };
            
            dropdownItems.forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    const mode = item.getAttribute('data-mode');
                    currentRadarMode = mode;
                    
                    // Update UI to show active mode
                    dropdownItems.forEach(i => i.classList.remove('mode-active'));
                    item.classList.add('mode-active');
                    
                    // Show success message with mode change
                    showSuccessMessage(`Radar mode changed to: ${modeNames[mode] || mode}`);
                    
                    // Apply mode-specific visual effects
                    applyModeEffects(mode);
                });
            });
        }
        
        function applyModeEffects(mode) {
            switch(mode) {
                case 'detection':
                    // Standard detection mode
                    showGridLines = true;
                    showBearingLines = true;
                    sweepSpeed = 45;
                    break;
                case 'doppler':
                    // Doppler analysis mode - slower sweep, more detailed
                    showGridLines = true;
                    showBearingLines = true;
                    sweepSpeed = 30;
                    break;
                case 'all':
                    // Full scanning mode
                    showGridLines = true;
                    showBearingLines = true;
                    sweepSpeed = 60;
                    break;
                case 'adas':
                    // Automotive ADAS - faster sweep, fewer grid lines
                    showGridLines = false;
                    showBearingLines = true;
                    sweepSpeed = 75;
                    break;
                case 'mining':
                    // Mining monitoring - slower, more grid lines
                    showGridLines = true;
                    showBearingLines = true;
                    sweepSpeed = 25;
                    break;
                case 'wifi':
                    // WiFi scanning - medium speed
                    showGridLines = false;
                    showBearingLines = false;
                    sweepSpeed = 50;
                    break;
            }
            
            // Update UI elements if they exist
            const speedSlider = document.getElementById('sweepSpeedSlider');
            const speedValueDisplay = document.getElementById('speedValueDisplay');
            const currentSpeedDisplay = document.getElementById('currentSpeedDisplay');
            const showGridToggle = document.getElementById('showGridToggle');
            const showBearingsToggle = document.getElementById('showBearingsToggle');
            
            if (speedSlider) speedSlider.value = sweepSpeed;
            if (speedValueDisplay) speedValueDisplay.innerText = sweepSpeed;
            if (currentSpeedDisplay) currentSpeedDisplay.innerText = sweepSpeed;
            if (showGridToggle) showGridToggle.checked = showGridLines;
            if (showBearingsToggle) showBearingsToggle.checked = showBearingLines;
            
            rotSpeedSpan.innerText = sweepSpeed + "°/s";
            renderFrame();
        }
        
        // ========== SETTINGS MODAL FUNCTION ==========
        function initSettingsModal() {
            const speedSlider = document.getElementById('sweepSpeedSlider');
            const speedValueDisplay = document.getElementById('speedValueDisplay');
            const currentSpeedDisplay = document.getElementById('currentSpeedDisplay');
            const ringsSlider = document.getElementById('ringsSlider');
            const ringsValueDisplay = document.getElementById('ringsValueDisplay');
            const bearingsSlider = document.getElementById('bearingsSlider');
            const bearingsValueDisplay = document.getElementById('bearingsValueDisplay');
            const showGridToggle = document.getElementById('showGridToggle');
            const showBearingsToggle = document.getElementById('showBearingsToggle');
            const showLabelsToggle = document.getElementById('showLabelsToggle');
            const resetBtn = document.getElementById('resetSettingsBtn');

            initHeatSignatureControls();

            speedValueDisplay.innerText = sweepSpeed;
            currentSpeedDisplay.innerText = sweepSpeed;
            ringsValueDisplay.innerText = ringCount;
            bearingsValueDisplay.innerText = bearingCount;
            rotSpeedSpan.innerText = sweepSpeed + "°/s";
            
            speedSlider.addEventListener('input', (e) => {
                const newSpeed = parseInt(e.target.value);
                sweepSpeed = newSpeed;
                speedValueDisplay.innerText = newSpeed;
                currentSpeedDisplay.innerText = newSpeed;
                rotSpeedSpan.innerText = newSpeed + "°/s";
            });
            
            ringsSlider.addEventListener('input', (e) => {
                ringCount = parseInt(e.target.value);
                ringsValueDisplay.innerText = ringCount;
                renderFrame();
            });
            
            bearingsSlider.addEventListener('input', (e) => {
                bearingCount = parseInt(e.target.value);
                bearingsValueDisplay.innerText = bearingCount;
                renderFrame();
            });
            
            showGridToggle.addEventListener('change', (e) => {
                showGridLines = e.target.checked;
                renderFrame();
            });
            
            showBearingsToggle.addEventListener('change', (e) => {
                showBearingLines = e.target.checked;
                renderFrame();
            });
            
            showLabelsToggle.addEventListener('change', (e) => {
                showCardinalLabels = e.target.checked;
                renderFrame();
            });
            
            resetBtn.addEventListener('click', () => {
                sweepSpeed = 45;
                ringCount = 4;
                bearingCount = 8;
                showGridLines = true;
                showBearingLines = true;
                showCardinalLabels = true;
                
                speedSlider.value = 45;
                ringsSlider.value = 4;
                bearingsSlider.value = 8;
                showGridToggle.checked = true;
                showBearingsToggle.checked = true;
                showLabelsToggle.checked = true;
                
                speedValueDisplay.innerText = 45;
                currentSpeedDisplay.innerText = 45;
                ringsValueDisplay.innerText = 4;
                bearingsValueDisplay.innerText = 8;
                rotSpeedSpan.innerText = "45.0°/s";
                renderFrame();
                showSuccessMessage('Settings reset to default values');
            });
            
            setInterval(() => {
                const lastSweepTimeSpan = document.getElementById('lastSweepTime');
                if (lastSweepTimeSpan && settingsModal && settingsModal._isShown) {
                    lastSweepTimeSpan.innerText = new Date().toLocaleTimeString();
                }
            }, 1000);
        }
        
        // ========== SECURITY MEASURES ==========
        function detectDevTools() {
            const element = new Image();
            Object.defineProperty(element, 'id', {
                get: function() {
                    devToolsOpen = true;
                    if (!consoleAlertShown) {
                        consoleAlertShown = true;
                        showSecurityAlert('Developer Tools detected! Access to console is blocked for security reasons.');
                        console.clear();
                    }
                    return '';
                }
            });
            console.log(element);
        }
        
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            showSecurityAlert('Right-click is disabled. This system is protected.');
            return false;
        });
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'F12') {
                e.preventDefault();
                showSecurityAlert('F12 is disabled. Developer tools are blocked.');
                return false;
            }
            if (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J' || e.key === 'C')) {
                e.preventDefault();
                showSecurityAlert('Keyboard shortcut blocked. Developer tools are not accessible.');
                return false;
            }
            if (e.ctrlKey && e.key === 'u') {
                e.preventDefault();
                showSecurityAlert('View source is disabled. Source code is protected.');
                return false;
            }
        });
        
        let devToolsCheckInterval;
        function checkDevTools() {
            const widthThreshold = window.outerWidth - window.innerWidth > 160;
            const heightThreshold = window.outerHeight - window.innerHeight > 160;
            if (widthThreshold || heightThreshold) {
                if (!devToolsOpen) {
                    devToolsOpen = true;
                    showSecurityAlert('Developer tools detected! Please close DevTools for security.');
                }
            } else {
                devToolsOpen = false;
            }
        }
        
        // ========== INITIALIZE RADAR ==========
        securityModal = new bootstrap.Modal(document.getElementById('securityModal'));
        successModal = new bootstrap.Modal(document.getElementById('successModal'));
        targetDetailsModal = new bootstrap.Modal(document.getElementById('targetDetailsModal'));
        settingsModal = new bootstrap.Modal(document.getElementById('settingsModal'));
        
        const settingsIcon = document.getElementById('settingsIcon');
        if (settingsIcon) {
            settingsIcon.addEventListener('click', () => {
                const systemTargetCount = document.getElementById('systemTargetCount');
                if (systemTargetCount) systemTargetCount.innerText = detectedTargets.length;
                const movingStatusSpan = document.getElementById('movingSystemStatus');
                if (movingStatusSpan) {
                    movingStatusSpan.innerText = movingTargetsActive ? 'ACTIVE' : 'INACTIVE';
                    movingStatusSpan.className = movingTargetsActive ? 'text-success' : 'text-warning';
                }
                settingsModal.show();
            });
        }
        
        if (targetCountBadge) {
            targetCountBadge.addEventListener('click', showTargetDetails);
        }
        
        initSettingsModal();
        initHeatSignature();
        initFullscreenButton();
        initRadarModeDropdown();
        
        handleResize();
        lastFrameTime = null;
        currentSweepAngle = 0;
        animationId = requestAnimationFrame(animateRadar);
        
        canvas.addEventListener('mousemove', onCanvasMouseMove);
        canvas.addEventListener('click', onCanvasClick);
        window.addEventListener('resize', handleResize);
        
        lastClickPoint = { x: null, y: null, angle: null, dist: null };
        
        canvas.addEventListener('mouseleave', () => {
            cursorXSpan.innerText = "---";
            cursorYSpan.innerText = "---";
            cursorAngleSpan.innerText = "---";
            cursorDistSpan.innerText = "---";
        });
        
        detectDevTools();
        devToolsCheckInterval = setInterval(checkDevTools, 1000);
        
        targetBadgeContainer.style.display = 'none';
        
        if (window.MovingTargetSystem) {
            movingTargetSystem = window.MovingTargetSystem;
            movingTargetSystem.start(handleMovingTargetUpdate);
            movingTargetsActive = true;
        }
        
        console.log("%cRADAR SYSTEM ACTIVE", "color: #00ff9d; font-size: 16px;");
        console.clear();
    };
})();
