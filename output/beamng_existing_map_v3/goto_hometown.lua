dofile('/art/hometown_hairpin_v3/load.lua')
local v=assert(be:getPlayerVehicle(0),'Player vehicle missing')
spawn.safeTeleport(v,vec3(-1572.5,-1445.5,114.4),quatFromDir(vec3(1,0,0)),nil,nil,nil,nil,true)
core_camera.setByName(0,'orbit')
return 'Hometown main road entrance'
