# scripts/js_spoofer.py
"""
This module generates dynamic JavaScript code for comprehensive browser spoofing.
"""

def generate_full_spoof_script(
    user_agent: str, platform: str, app_version: str, vendor: str,
    width: int, height: int, pixel_ratio: float, color_depth: int,
    webgl_vendor: str, webgl_renderer: str,
    device_memory: int, hardware_concurrency: int,
    timezone: str
) -> str:
    """
    Generates a JS string to override navigator, screen, WebGL, Intl, and Date objects.
    """
    avail_height = height - 40 

    return f"""
    (() => {{

        // --- Basic Navigator, Hardware, Screen, etc. Spoofing (Unchanged) ---
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
        Object.defineProperty(navigator, 'userAgent', {{ get: () => `{user_agent}` }});
        Object.defineProperty(navigator, 'platform', {{ get: () => `{platform}` }});
        Object.defineProperty(navigator, 'appVersion', {{ get: () => `{app_version}` }});
        Object.defineProperty(navigator, 'vendor', {{ get: () => `{vendor}` }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {device_memory} }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hardware_concurrency} }});
        Object.defineProperty(screen, 'width', {{ get: () => {width} }});
        Object.defineProperty(screen, 'height', {{ get: () => {height} }});
        Object.defineProperty(screen, 'availWidth', {{ get: () => {width} }});
        Object.defineProperty(screen, 'availHeight', {{ get: () => {avail_height} }});
        Object.defineProperty(screen, 'colorDepth', {{ get: () => {color_depth} }});
        Object.defineProperty(screen, 'pixelDepth', {{ get: () => {color_depth} }});
        Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {pixel_ratio} }});
        Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => 5 }});
        Object.defineProperty(navigator, 'msMaxTouchPoints', {{ get: () => 5 }});
        window.ontouchstart = null;
        try {{
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(pname) {{
                if (pname === 37445) return `{webgl_vendor}`;
                if (pname === 37446) return `{webgl_renderer}`;
                return getParameter.call(this, pname);
            }};
        }} catch (e) {{ console.error('Failed to spoof WebGL:', e); }}
        
        // --- Intl.DateTimeFormat Spoofing (Unchanged) ---
        try {{
            const originalDateTimeFormat = Intl.DateTimeFormat;
            Intl.DateTimeFormat = function(locales, options) {{
                return new originalDateTimeFormat(locales, {{ ...options, timeZone: '{timezone}' }});
            }};
        }} catch (e) {{ console.error('Failed to spoof Intl.DateTimeFormat:', e); }}

        // --- Date Object Override (CRITICAL FIX FOR TIMEZONE LEAK) ---
        try {{
            const originalDate = Date;

            // Create a new Date class that extends the original
            class SpoofedDate extends originalDate {{
                constructor(...args) {{
                    // Call the original Date constructor
                    super(...args);
                }}

                // Override methods that leak the host timezone
                toString() {{
                    return this.toLocaleString('en-US', {{ timeZone: '{timezone}'  }});
                }}

                toLocaleString(...args) {{
                    const [locales, options] = args;
                    return super.toLocaleString(locales, {{ ...options, timeZone: '{timezone}' }});
                }}

                toLocaleDateString(...args) {{
                    const [locales, options] = args;
                    return super.toLocaleDateString(locales, {{ ...options, timeZone: '{timezone}' }});
                }}

                toLocaleTimeString(...args) {{
                    const [locales, options] = args;
                    return super.toLocaleTimeString(locales, {{ ...options, timeZone: '{timezone}' }});
                }}
            }}

            // Replace the global Date object with our spoofed version
            window.Date = SpoofedDate;
        }} catch(e) {{
            console.error('Failed to spoof Date object:', e);
        }}

    }})();
    """