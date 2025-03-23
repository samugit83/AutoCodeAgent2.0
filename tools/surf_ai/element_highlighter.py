class ElementHighlighter:
    def __init__(self, logger):
        self.logger = logger

    async def apply_highlight(self, page):
        try:
            await page.wait_for_timeout(2000)
            await page.evaluate(self._highlight_script())
        except Exception as e:
            self.logger.debug(f"Highlight failed: {str(e)}")

    async def remove_highlight(self, page):
        try:
            await page.evaluate(self._remove_highlight_script())
        except Exception as e:
            self.logger.debug(f"Remove highlight failed: {str(e)}") 

    def _highlight_script(self):
        return """
            (function() {
                let counter = 1;
                const getRandomColor = () => {
                    const hue = Math.floor(Math.random() * 360);
                    const saturation = 70 + Math.floor(Math.random() * 20);
                    const lightness = 30 + Math.floor(Math.random() * 10);
                    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
                };

                const interactiveSelectors = [ 
                    'input', 'textarea', 'button', 'select', 'output',
                    'a[href]', 'area[href]',
                    '[contenteditable]',
                    '[tabindex]:not([tabindex="-1"])',
                    '[onclick]', '[ondblclick]', '[onchange]', '[onsubmit]', '[onkeydown]',
                    'audio[controls]', 'video[controls]',
                    'details', 'details > summary',
                    '[role="button"]', '[role="checkbox"]', '[role="radio"]',
                    '[role="link"]', '[role="textbox"]', '[role="searchbox"]',
                    '[role="combobox"]', '[role="listbox"]', '[role="menu"]', 
                    '[role="menuitem"]', '[role="slider"]', '[role="switch"]',
                    '[role="tab"]', '[role="treeitem"]', '[role="gridcell"]',
                    '[role="option"]', '[role="spinbutton"]', '[role="scrollbar"]',
                    'iframe', 'object', 'embed' 
                ];

                // Select only visible, interactive elements that haven't been highlighted yet.
                const elements = Array.from(document.querySelectorAll('*')).filter(el => {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' &&
                        style.visibility === 'visible' &&
                        el.offsetParent !== null &&
                        interactiveSelectors.some(selector => el.matches(selector)) &&
                        !el.dataset.highlightNumber;
                });

                elements.forEach(el => {
                    // Assign a unique highlight number without modifying element layout.
                    const number = counter++;
                    el.dataset.highlightNumber = number;
                    const color = getRandomColor();

                    // Get the element's position and size.
                    const rect = el.getBoundingClientRect();

                    // Create an overlay using fixed positioning.
                    const overlay = document.createElement('div');
                    overlay.className = 'surf-ai-highlight-overlay';
                    overlay.dataset.highlightNumber = number;
                    overlay.style.position = 'fixed';
                    overlay.style.top = rect.top + 'px';
                    overlay.style.left = rect.left + 'px';
                    overlay.style.width = rect.width + 'px';
                    overlay.style.height = rect.height + 'px';
                    overlay.style.border = '2px solid ' + color;
                    overlay.style.boxSizing = 'border-box';
                    overlay.style.pointerEvents = 'none';
                    overlay.style.zIndex = '10000';

                    // Create and style the label.
                    const label = document.createElement('span');
                    label.className = 'surf-ai-highlight-label'; 
                    label.textContent = number;
                    label.style.position = 'absolute';
                    label.style.top = '-7px';
                    label.style.left = '-7px';
                    label.style.backgroundColor = color;
                    label.style.fontFamily = 'Arial';
                    label.style.color = 'white';
                    label.style.display = 'flex';
                    label.style.alignItems = 'center';
                    label.style.justifyContent = 'center';
                    label.style.fontSize = '16px';
                    label.style.height = '18px';
                    label.style.padding = '0 2px';  
                    label.style.fontWeight = 'bold';
                    label.style.borderRadius = '2px';

                    overlay.appendChild(label);
                    document.body.appendChild(overlay);
                });
            })();
        """

    def _remove_highlight_script(self):
        return """
            (function() {
                document.querySelectorAll('.surf-ai-highlight-overlay').forEach(overlay => {
                    overlay.parentNode.removeChild(overlay);
                });
                document.querySelectorAll('[data-highlight-number]').forEach(el => {
                    delete el.dataset.highlightNumber;
                });
            })();
        """
