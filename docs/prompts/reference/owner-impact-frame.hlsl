// Input textures and samplers
Texture2D<float4> _MainTex : register(t0);
SamplerState sampler_MainTex : register(s0);

cbuffer HakiImpactBuffer : register(b1)
{
    float2 _ImpactCenter;    // Screen space epicenter of the hit (e.g., [0.5, 0.5])
    float  _Time;            // Global time for animated lightning flickering
    float  _ImpactProgress;  // 0.0 (just hit) to 1.0 (fading out)
    float  _ShockwaveRadius; // Controls the expansion speed of the ring
    float3 _LightningColor;  // Primary streak color (Try vivid Red: [1.0, 0.1, 0.2])
    float3 _CoreColor;       // Inner blast glow (Try deep Purple or Gold)
};

struct VS_OUTPUT
{
    float4 Position : SV_POSITION;
    float2 UV       : TEXCOORD0;
};

// High-fidelity pseudo-random noise function for organic lightning shapes
float Hash21(float2 p) 
{
    return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453123);
}

// 2D Value Noise
float Noise2D(float2 p) 
{
    float2 i = floor(p);
    float2 f = frac(p);
    f = f * f * (3.0 - 2.0 * f); // Smoothstep interpolation
    
    float a = Hash21(i);
    float b = Hash21(i + float2(1.0, 0.0));
    float c = Hash21(i + float2(0.0, 1.0));
    float d = Hash21(i + float2(1.0, 1.0));
    
    return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
}

// Generates jagged, fractal-like lightning bands
float GetLightningStreak(float2 uv, float seed)
{
    // Distort coordinates spherically from the impact center
    float2 toCenter = uv - _ImpactCenter;
    float angle = atan2(toCenter.y, toCenter.x);
    float dist = length(toCenter);
    
    // Create irregular lightning spikes radiating outward
    float noisePattern = Noise2D(float2(angle * 8.0, dist * 15.0 - _Time * 25.0 + seed));
    noisePattern += Noise2D(float2(angle * 16.0, dist * 5.0)) * 0.5;
    
    // Sharpen the noise into narrow, high-contrast streaks
    float streak = saturate(1.0 - abs(noisePattern - 0.5) / 0.02);
    return pow(streak, 4.0); // Extreme contrast to give it that hard-edged anime look
}

float4 main(VS_OUTPUT input) : SV_TARGET
{
    // 1. Screen chromatic distortion (Stylized Haki reality warping)
    float2 dirFromCenter = input.UV - _ImpactCenter;
    float distFromCenter = length(dirFromCenter);
    
    // Push screen pixels away from center based on impact progress to create a punchy distortion wave
    float waveMask = saturate(1.0 - abs(distFromCenter - _ShockwaveRadius) / 0.1);
    float2 distortedUV = input.UV - (dirFromCenter * waveMask * 0.05 * (1.0 - _ImpactProgress));
    
    // Sample scene with chromatic aberration
    float4 sceneColor;
    sceneColor.r = _MainTex.Sample(sampler_MainTex, distortedUV + float2(0.005, 0.0)).r;
    sceneColor.g = _MainTex.Sample(sampler_MainTex, distortedUV).g;
    sceneColor.b = _MainTex.Sample(sampler_MainTex, distortedUV - float2(0.005, 0.0)).b;
    sceneColor.a = 1.0;

    // 2. High-Contrast Stylized Posterization & Inversion
    // One Piece impacts crush intermediate shades into hard black/white values
    float luma = dot(sceneColor.rgb, float3(0.299, 0.587, 0.114));
    float3 crushedScene = luma < 0.25 ? float3(0.0, 0.0, 0.0) : sceneColor.rgb;
    
    // Invert bright regions near the explosion epicenter
    if (distFromCenter < _ShockwaveRadius * 0.7 && _ImpactProgress < 0.3)
    {
        crushedScene = 1.0 - crushedScene;
    }

    // 3. Generate High-Fidelity Procedural Lightning
    // Generate layered streaks with distinct seeds for visual complexity
    float lightning1 = GetLightningStreak(input.UV, 1.23);
    float lightning2 = GetLightningStreak(input.UV, 5.67);
    float combinedLightning = saturate(lightning1 + lightning2);
    
    // Fade out lightning over distance and time
    combinedLightning *= saturate(1.2 - distFromCenter);
    combinedLightning *= (1.0 - _ImpactProgress);

    // Apply color grading to the lightning: Intense core fading to the primary shock color
    float3 lightningFinalColor = lerp(_LightningColor, _CoreColor * 3.0, pow(combinedLightning, 3.0));

    // 4. Ink-Splatter Haki Center Aura
    // Create the jagged, dark ink-blob field right at the focal point of the fist/sword clash
    float inkNoise = Noise2D(input.UV * 25.0 + _Time * 10.0);
    float inkRadius = 0.15 * (1.0 - _ImpactProgress);
    float inkMask = smoothstep(inkRadius + 0.05, inkRadius, distFromCenter + inkNoise * 0.08);
    
    // 5. Composite Final Image
    // Layer order: Background -> Crushed Scene -> Ink Splatter -> Lightning Emissive Glow
    float3 finalColor = lerp(crushedScene, float3(0.02, 0.0, 0.05), inkMask); // Dark ink bleed
    finalColor += lightningFinalColor * combinedLightning * 2.5;              // Overtop lightning emission

    return float4(finalColor, 1.0);
}
