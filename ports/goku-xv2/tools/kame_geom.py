"""Where the Kamehameha points. Measured, not guessed (2026-10-10, hitbox probe at Full action frame 20, gd.hitboxes px/py/pz):
the right hand's local axes in world (facing right), each a unit vector:
    x_l = (-0.454, -0.850, -0.264)   y_l = (-0.122, 0.352, -0.927)   z_l = (0.881, -0.389, -0.264)
(the fire pose points the hand's +Z forward, 22 degrees down and 15 degrees into the screen). The beam must run along world +X, so in the
hand's frame it runs along D = (world_x . x_l, . y_l, . z_l) = (-0.454, -0.122, 0.881). Hitbox offsets (x, y, z) and the effect meshes use
it; both the hitbox frame and the effect frame are the hand joint's (the axis test showed the same axes). Offsets are in model units: the
engine multiplies them by the fighter's scale SCALE (offset 10 read back as 14.3), so world length = SCALE x authored length."""
import math

SCALE = 1.43
D = (-0.454, -0.122, 0.881)
# emitter rotation (radians, X then Y) taking a mesh's +Z onto D: Rx(a) then Ry(b)
A = math.asin(-D[1])
B = math.asin(D[0] / math.cos(A))
ROT = [A, B, 0.0]


def along(k):
    return (D[0] * k, D[1] * k, D[2] * k)
