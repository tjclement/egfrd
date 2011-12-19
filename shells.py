#!/usr/bin/python


class Others(object):

    # stuff for hasShell subclasses
    def shell_list_for_single(self):
        return self.shell_list
    def shell_list_for_other(self):
        return self.shell_list

    # stuff for testShell subclasses
    def get_neighbor_shell_list(self, neighbor):
        # note that this returns the list of shells, NOT dr, dz_right, dz_left
        return neighbor.shell_list_for_other()

class NonInteractionSingles(object):

    # stuff for hasShell subclasses
    def shell_list_for_single(self):
        pass    # needs to be overloaded
    def shell_list_for_other(self):
        pass    # needs to be overloaded

    # stuff for testShell subclasses
    def get_neighbor_shell_list(self, neighbor):
        # note that this returns the list of shells, NOT dr, dz_right, dz_left
        return neighbor.shell_list_for_single()

##################################
class hasShell(object):

    def __init__(self, testShell):
        self.testShell = testShell

#    def shell_list(self):
#            return self.shell_list

#######################
class hasSphericalShell(hasShell):
# The testShell is now converted into smt that we can use in the domain instance

    def __init__(self, sphericaltestShell):

        hasShell.__init__(self, sphericaltestShell)

        self.center = self.sphericaltestShell.center
        self.radius = self.sphericaltestShell.radius
        self.shell = self.testShell.create_new_shell(self.radius, self.domain_id)

    # methods to size up a shell to this shell
    def get_dr_dzright_dzleft_to_shell(self, shell, domain_to_scale, r, z_right, z_left):
        # This will scale the 'domain_to_scale' (a cylinder) using the 'shell_appearance' as the limiting shell
        # CylindricaltestShell ('domain_to_scale') -> SphericalShell ('self' with 'shell_appearance')

        assert type(shell, Sphere)        # because the shell actually is part of the current object

        # Do Laurens' algorithm (part1)
        shell_position = shell.shape.position
        shell_radius = shell.shape.radius

        # get the reference point and orientation of the domain to scale
        reference_point = domain_to_scale.get_referencepoint()
        orientation_vector = domain_to_scale.get_orientation_vector()

        # determine on what side the midpoint of the shell is relative to the reference_point
        shell_position_t = world.cyclic_transpose (shell_position, reference_point)
        ref_to_shell_vec = shell_position_t - reference_point
        ref_to_shell_z = numpy.dot(ref_to_shell_vec, orientation_vector)

        # if the shell is on the side of orientation_vector -> use z_right
        # also use this one if the shell is in plane with the reference_point
        if ref_to_shell_z >= 0:
            direction = 1           # improve direction specification such that following calculations still work
                                    # Otherwise problems when direction = 0
            scale_angle = domain_to_scale.get_right_scalingangle()
            scale_center_r, scale_center_z = domain_to_scale.get_right_scalingcenter() 
            r1_function =  domain_to_scale.r_right
            z1_function = domain_to_scale.z_right
            z2_function = domain_to_scale.z_left
            z1 = z_right
            z2 = z_left
        # else -> use z_left
        else:
            direction = -1
            scale_angle = domain_to_scale.get_left_scalingangle()
            scale_center_r, scale_center_z = domain_to_scale.get_left_scalingcenter() 
            r1_function =  domain_to_scale.r_left
            z1_function = domain_to_scale.z_left
            z2_function = domain_to_scale.z_right
            z1 = z_left
            z2 = z_right

        # calculate ref_to_shell_r/z in the cylindrical coordinate system on the right/left side
        ref_to_shell_z_vec = ref_to_shell_z * orientation_vector
        ref_to_shell_r_vec = ref_to_shell_vec - ref_to_shell_z_vec
        ref_to_shell_r = length(ref_to_shell_r_vec)
        ref_to_shell_z = abs(ref_to_shell_z)

        # get the center from which linear scaling will take place
        scale_center_to_shell_r = ref_to_shell_r - scale_center_r
        scale_center_to_shell_z = ref_to_shell_z - scale_center_z


        # calculate the angle shell_angle of the vector from the scale center to the shell with the vector
        # to the scale center (which is +- the orientation_vector)
        shell_angle = math.atan(scale_center_to_shell_r/scale_center_to_shell_z)

        psi = shell_angle - scale_angle

        ### check what situation arrises
        # The shell can hit the cylinder on the flat side (situation 1),
        #                                on the edge (situation 2),
        #                                or on the round side (situation 3).
        # I think this also works for scale_angle == 0 and scale_angle == Pi/2
        if psi <= -scale_angle:
        # The midpoint of the shell lies on the axis of the cylinder
            situation = 1

        elif -scale_angle < psi and psi < 0:
        # The spherical shell can touch the cylinder on its flat side or its edge
            if scale_angle == Pi/2.0:
                r_tan_scale_angle = 0
            else:
                # scale_angle == 0 should not get here
                r_tan_scale_angle = abs(scale_center_to_shell_r)/math.tan(scale_angle)
                                    # TODO the abs may be wrong/unnecessary

            shell_radius_thres = scale_center_to_shell_z - r_tan_scale_angle
            if shell_radius < shell_radius_thres:
                situation = 1
            else:
                situation = 2

        elif 0 <= psi and psi < (Pi/2.0 - scale_angle):
        # The (spherical) shell can touch the cylinder on its edge or its radial side
            tan_scale_angle = math.tan(scale_angle)                             # scale_angle == Pi/2 should not get here
            shell_radius_thres = abs(scale_center_to_shell_r) - scale_center_to_shell_z * tan_scale_angle  # TODO same here
            if shell_radius > shell_radius_thres:
                situation = 2
            else:
                situation = 3

        elif (Pi/2.0 - scale_angle) <= psi:
        # The shell is always only on the radial side of the cylinder
            situation = 3

        else:
        # Don't know how we would get here, but it shouldn't happen
            raise RuntimeError('Error: psi was not in valid range. psi = %s, scale_angle = %s, shell_angle = %s' %
                               (FORMAT_DOUBLE % psi, FORMAT_DOUBLE % scale_angle, FORMAT_DOUBLE % shell_angle))


        ### Get the right values for z and r for the given situation
        if situation == 1:      # the spherical shell hits cylinder on the flat side
            z1_new = min(z1, (ref_to_shell_z - shell_radius)/SAFETY)
            r_new  = min(r,  r1_function(single1, single2, r0, z1_new))

        elif situation == 2:    # shell hits sphere on the edge
            shell_radius_sq = shell_radius*shell_radius
            ss_sq = (scale_center_to_shell_z**2 + scale_center_to_shell_r**2)
            scale_center_to_shell_len = math.sqrt(ss_sq)
            sin_scale_angle = math.sin(scale_angle)
            sin_psi = math.sin(psi)
            cos_psi = math.cos(psi)
            scale_center_shell_dist = (scale_center_to_shell_len * cos_psi - math.sqrt(shell_radius_sq - ss_sq*sin_psi*sin_psi) )
            # FIXME UGLY FIX BELOW
#            scale_center_shell_dist /= 1.1

            if scale_angle <= Pi/4:
                z1_new = min(z1, (scale_center_z + cos_scale_angle * scale_center_shell_dist)/SAFETY)
                r_new  = min(r, r1_function(single1, single2, r0, z1_new))
            else:
                r_new = min(r, (scale_center_r + sin_scale_angle * scale_center_shell_dist)/SAFETY)
                z1_new = min(z1, z1_function(single1, single2, r0, r_new))

        elif situation == 3:    # shell hits cylinder on the round side
            r_new = min(r, (ref_to_shell_r - shell_radius)/SAFETY)
            z1_new = min(z1, z1_function(single1, single2, r0, r_new))
        else:
            raise RuntimeError('Bad situation for cylindrical shell making to sphere.')

        z2_new = min(z2, z2_function(single1, single2, r0, r_new))

        # switch the z values in case it's necessary. r doesn't have to be switched.
        r = r_new
        if direction >= 0.0:
            z_right = z1_new
            z_left  = z2_new
        else:
            z_right = z2_new
            z_left  = z1_new

        return (r, z_right, z_left)


    def get_radius_to_shell(self, shell, domain_to_scale):
        # SphericaltestShell ('domain_to_scale') -> SphericalShell ('self' with 'shell_appearance')

        assert type(shell, Sphere)        # because the shell actually originated here
        # Do simple distance calculation to sphere

        scale_point = domain_to_scale.center
        r = self.world.distance(shell.shape, scale_point)
        return r

#####
class SphericalSingle(hasSphericalShell, NonInteractionSingles):

    # these return potentially corrected dimensions
    def shell_list_for_single(self):
        min_radius = self.pid_particle_pair[1].radius * Domain.MULTI_SHELL_FACTOR
        if  self.shell.shape.radius < min_radius:
            fake_shell = self.shell_object.create_new_shell(min_radius, self.domain_id)
            return [(self.shell_id, fake_shell), ]
        else:
            return self.shell_list

    def shell_list_for_other(self):
        min_radius = self.pid_particle_pair[1].radius * Domain.SINGLE_SHELL_FACTOR
        if self.shell.shape.radius < min_radius:
            fake_shell = self.shell_object.create_new_shell(min_radius, self.domain_id)
            return [(self.shell_id, fake_shell), ]
        else:
            return self.shell_list

#####
class SphericalPair(hasSphericalShell, Others):

    pass

#####
class Multi(hasSphericalShell, Others):

    pass

#########################
class hasCylindricalShell(hasShell):

    def __init__(self, cylindricaltestShell):
        self.center = uitrekenen zie interactions
        self.radius = cylindricaltestShell.dr
        self.half_length = uitrekenen zie interactions

    def get_center:
        pass

    def get_dr_dzright_dzleft_to_shell(self, shell, domain_to_scale, r, z_right, z_left):
        # This will scale the 'domain_to_scale' (a cylinder) using the 'shell_appearance' as the limiting shell
        # CylindricaltestShell ('domain_to_scale') -> CylindricalShell ('self' with 'shell_appearance')

        if __debug__:
            log.debug('cylinder')

        assert type(shell, Cylinder)        # because the shell actually originated here
        # Do Laurens' algorithm (part2)

        shell_position = shell.shape.position
        shell_radius = shell.shape.radius
        shell_half_length = shell.shape.half_length


        # get the reference point and orientation of the domain to scale
        reference_point = domain_to_scale.get_referencepoint()
        orientation_vector = domain_to_scale.get_orientation_vector()

        # determine on what side the midpoint of the shell is relative to the reference_point
        shell_position_t = world.cyclic_transpose (shell_position, reference_point)
        ref_to_shell_vec = shell_position_t - reference_point
        ref_to_shell_z = numpy.dot(ref_to_shell_vec, orientation_vector)

        # if the shell is on the side of orientation_vector -> use z_right
        # also use this one if the shell is in plane with the reference_point
        if ref_to_shell_z >= 0:
            direction = 1           # improve direction specification such that following calculations still work
                                    # Otherwise problems when direction = 0
            scale_angle = domain_to_scale.get_right_scalingangle()
            scale_center_r, scale_center_z = domain_to_scale.get_right_scalingcenter() 
            r1_function =  domain_to_scale.r_right
            z1_function = domain_to_scale.z_right
            z2_function = domain_to_scale.z_left
            z1 = z_right
            z2 = z_left
        # else -> use z_left
        else:
            direction = -1
            scale_angle = domain_to_scale.get_left_scalingangle()
            scale_center_r, scale_center_z = domain_to_scale.get_left_scalingcenter() 
            r1_function =  domain_to_scale.r_left
            z1_function = domain_to_scale.z_left
            z2_function = domain_to_scale.z_right
            z1 = z_left
            z2 = z_right

        # calculate ref_to_shell_r/z in the cylindrical coordinate system on the right/left side
        ref_to_shell_z_vec = ref_to_shell_z * orientation_vector
        ref_to_shell_r_vec = ref_to_shell_vec - ref_to_shell_z_vec
        ref_to_shell_r = length(ref_to_shell_r_vec)
        ref_to_shell_z = abs(ref_to_shell_z)

        # calculate the distances in r/z from the scaling center to the shell
        scale_center_to_shell_r = ref_to_shell_r - scale_center_r
        scale_center_to_shell_z = ref_to_shell_z - scale_center_z

        # get angles
        omega = math.atan( (scale_center_to_shell_r - shell_radius) / (scale_center_to_shell_z - shell_half_length) )
        omega += Pi

        if __debug__:
            log.debug('omega = %s' % FORMAT_DOUBLE % omega)

        if omega <= scale_angle:
            # shell hits the scaling cylinder on top
            z1_new = min(z1, (ref_to_shell_z - shell_half_length)/SAFETY)
            r_new  = min(r,  r1_function(single1, single2, r0, z1_new))
        else:
            # shell hits the scaling cylinder on the radial side
            r_new = min(r, (ref_to_shell_r) - shell_radius)/SAFETY)
            z1_new = min(z1, z1_function(single1, single2, r0, r_new))
        z2_new = min(z2, z2_function(single1, single2, r0, r_new))


        # switch the z values in case it's necessary. r doesn't have to be switched.
        r = r_new
        if direction >= 0.0:
            z_right = z1_new
            z_left  = z2_new
        else:
            z_right = z2_new
            z_left  = z1_new

        return (r, z_right, z_left)

    def get_radius_to_shell(self, shell, domain_to_scale):
        # SphericaltestShell ('domain_to_scale') -> CylindricalShell ('self' with 'shell_appearance')

        assert type(shell, Cylinder)        # because the shell actually originated here
        # Do simple distance calculation to cylinder

        scale_point = domain_to_scale.center
        r = self.world.distance(shell.shape, scale_point)
        return r

#####
class PlanarSurfaceSingle(hasCylindricalShell, NonInteractionSingles):

    # these return corrected dimensions, since we reserve more space for the NonInteractionSingle
    def shell_list_for_single(self):
        min_radius = self.pid_particle_pair[1].radius * Domain.MULTI_SHELL_FACTOR
        if self.shell.shape.radius < min_radius:
            half_length = self.shell.shape.half_length
            fake_shell = self.shell_object.create_new_shell(min_radius, half_length, self.domain_id)
            return [(self.shell_id, fake_shell), ]
        else:
            return self.shell_list

    def shell_list_for_other(self):
        min_radius = self.pid_particle_pair[1].radius * Domain.SINGLE_SHELL_FACTOR
        if self.shell.shape.radius < min_radius:
            half_length = self.shell.shape.half_length
            fake_shell = self.shell_object.create_new_shell(min_radius, half_length, self.domain_id)
            return [(self.shell_id, fake_shell), ]
        else:
            return self.shell_list

#####
class CylindricalSurfaceSingle(hasCylindricalShell, NonInteractionSingles):

    # these return corrected dimensions, since we reserve more space for the NonInteractionSingle
    def shell_list_for_single(self):
        min_half_length = self.pid_particle_pair[1].radius * Domain.MULTI_SHELL_FACTOR
        if self.shell.shape.half_length < min_half_length:
            radius = self.shell.shape.radius
            fake_shell = self.shell_object.create_new_shell(radius, min_half_length, domain_id)
            return [(self.shell_id, fake_shell), ]
        else:
            return self.shell_list

    def shell_list_for_other(self):
        min_half_length = self.pid_particle_pair[1].radius * Domain.SINGLE_SHELL_FACTOR
        if self.shell.shape.half_length < min_half_length:
            radius = self.shell.shape.radius
            fake_shell = self.shell_object.create_new_shell(radius, min_half_length, domain_id)
            return [(self.shell_id, fake_shell), ]
        else:
            return self.shell_list

#####
class PlanarSurfacePair(hasCylindricalShell, Others):
class PlanarSurfaceInteraction(hasCylindricalShell, Others):
class CylindricalSurfacePair(hasCylindricalShell, Others):
class CylindricalSurfaceInteraction(hasCylindricalShell, Others):
class MixedPair3D2D(hasCylindricalShell, Others):
#class MixedPair3D1D(hasCylindricalShell):


#######################################################
#######################################################
class testShell(object):

    def __init__(self):
        self.shell = None

    def get_neighbors(self):
        searchpoint = self.get_searchpoint()
        radius = self.get_searchradius()
        return self.geometrycontainer.get_neigbors(searchpoint, radius)

########################
class SphericaltestShell(testShell):

    def __init__(self):
        self.radius = 0
        self.center = None

    def determine_possible_shell(self):
        neighbors = self.get_neighbors()
        min_radius = self.get_min_radius()
        max_radius = self.get_max_radius()

        radius = max_radius
        for neighbor in neighbors:

            shell_list = self.get_neighbor_shell_list(neighbor)
            for _, shell_appearance in shell_list:
                new_radius = neighbor.shell_object.get_radius_to_shell(shell_appearance, self)
                # if the newly calculated dimensions are smaller than the current one, use them
                radius = min(radius, new_radius)

                if radius < min_radius:
                    radius = None
                    break

        if radius:
            self.radius = radius
            return radius
        else
            return None

    def create_new_shell(self, radius, domain_id):
        position = self.center
        return SphericalShell(domain_id, Sphere(position, radius))

    def get_searchpoint(self):
        return self.center
    def get_searchradius(self):
        return self.geometrycontainer.max()

    def get_max_radius(self):
        return shell_container.get_max_shell_size()

#####
class SphericalSingletestShell(testSphericalShell, NonInteractionSingles):

    self.center = particle_position

    def get_min_radius(self):
        return particle_radius * MULTI_SHELL_FACTOR     # the minimum radius of a NonInteractionSingle

#####
class SphericalPairtestShell(testSphericalShell, Others):

    self.center = calculate CoM
    def get_min_radius:
        return calculate_min_radius_see_sphericalpair


##########################
class CylindricaltestShell(testShell):

    def __init__(self):
        self.position = calc from self.dr
        self.radius =        self.dz_right
        self.half_length =        self.dz_left

    def determine_possible_shell(self):
        neighbors = self.get_neighbors()
        min_dr_dzright_dzleft = self.get_min_dr_dzright_dzleft()
        max_dr_dzright_dzleft = self.get_max_dr_dzright_dzleft()

        dr_dzright_dzleft = max_dr_dzright_dzleft
        for neighbor in neighbors:

            shell_list = self.get_neighbor_shell_list(neighbor)
            for _, shell_appearance in shell_list:
                new_dr_dzright_dzleft = neighbor.get_dr_dzright_dzleft(shell_appearance, self)

                # if the newly calculated dimensions are smaller than the current one, use them
                dr_dzright_dzleft = min(dr_dzright_dzleft, new_dr_dzright_dzleft)
                if dr_dzright_dzleft < min_dr_dzright_dzleft:
                    dr_dzright_dzleft = None
                    break

        if dr_dzright_dzleft:
            return self.create_new_shell(dr_dzright_dzleft)
        else
            return None

    def create_new_shell(self, radius, half_length, domain_id):
        position = self.position
        orientation = self.get_orientation_vector()
        return CylindricalShell(domain_id, Cylinder(position, radius, orientation, half_length))

    # default functions for evaluating z_right/z_left/r after one of parameters changed
    def r_right(self, z_right):
        return self.drdz_right * z_right + self.r0_right
    def z_right(self, r_right):
        return self.dzdr_right * r_right + self.z0_right
    def r_left(self, z_left):
        return self.drdz_left * z_left + self.r0_left
    def z_left(self, r_left):
        return self.dzdr_left * r_left + self.z0_left

    def get_max_dr_dzright_dzleft(self):
        pass    # todo, we should be able to derive this from the scaling parameters and searchpoint

#####
class PlanarSurfaceSingletestShell(CylindricaltestShell, NonInteractionSingles):

    def __init__(self):
        # scaling parameters
        self.dzdr_right = 0.0
        self.drdz_right = numpy.inf
        self.r0_right   = 0.0
        self.z0_right   = particle_radius
        self.dzdr_left  = 0.0
        self.drdz_left  = numpy.inf
        self.r0_left    = 0.0
        self.z0_left    = particle_radius

    def get_orientation_vector(self):
        return structure.shape.unit_z   # just copy from structure

    def get_searchpoint(self):
        return particle_pos

    def get_referencepoint(self):
        return particle_pos

    def get_min_dr_dzright_dzleft(self):
        dr = particle_radius * MULTI_SHELL_FACTOR
        dz_right = particle_radius
        dz_left = particle_radius
        return (dr, dz_right, dz_left)

    def get_max_dr_dzright_dzleft(self):
        dr = math.sqrt(geometrycontainer_max**2 - particle_radius**2)
        dz_right = particle_radius
        dz_left = particle_radius
        return (dr, dz_right, dz_left)

    def get_right_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note that we assume cylindrical symmetry
        # Note also that it is relative to the 'side' (right/left) of the cylinder
        return 0, particle_radius

    def get_left_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note that we assume cylindrical symmetry
        # Note also that it is relative to the 'side' (right/left) of the cylinder
        return 0, particle_radius 

    def get_right_scalingangle(self):
        return Pi/2.0

    def get_left_scalingangle(self):
        return Pi/2.0

#####
class PlanarSurfacePairtestShell(hasCylindricalShell, Others):

    def __init__(self):
        # scaling parameters
        self.dzdr_right = 0.0
        self.drdz_right = numpy.inf
        self.r0_right   = 0.0
        self.z0_right   = max(particle_radius1, particle_radius2)
        self.dzdr_left  = 0.0
        self.drdz_left  = numpy.inf
        self.r0_left    = 0.0
        self.z0_left    = max(particle_radius1, particle_radius2)

    def get_orientation_vector(self):
        return structure.shape.unit_z

    def get_searchpoint(self):
        return CoM

    def get_referencepoint(self):
        return CoM

    def get_min_dr_dzright_dzleft(self):
        do calculation
        return (dr, dz_right, dz_left)

    def get_max_dr_dzright_dzleft(self):
        dr = math.sqrt(geometrycontainer_max**2 - particle_radius**2)
        dz_right = particle_radius
        dz_left = particle_radius
        return (dr, dz_right, dz_left)
        
#####
class CylindricalSurfaceSingletestShell(CylindricaltestShell, NonInteractionSingles):

    def __init__(self):
        # scaling parameters
        self.dzdr_right = numpy.inf
        self.drdz_right = 0.0
        self.r0_right   = particle_radius
        self.z0_right   = 0.0
        self.dzdr_left  = numpy.inf
        self.drdz_left  = 0.0
        self.r0_left    = particle_radius
        self.z0_left    = 0.0

    def orientation_vector(self):
        return structure.shape.unit_z   # just copy from structure

    def get_searchpoint(self):
        return particle_pos

    def get_referencepoint(self):
        return particle_pos

    def get_min_dr_dzright_dzleft(self):
        dr = particle_radius
        dz_right = particle_radius * MULTI_SHELL_FACTOR
        dz_left = particle_radius * MULTI_SHELL_FACTOR
        return (dr, dz_right, dz_left)

    def get_max_dr_dzright_dzleft(self):
        dr = particle_radius
        dz_right = math.sqrt(geometrycontainer_max**2 - particle_radius**2)
        dz_left = dz_right
        return (dr, dz_right, dz_left)

    def get_right_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note1: we assume cylindrical symmetry
        # Note2: it is relative to the 'side' (right/left) of the cylinder
        # Note3: we assume that the r-axis goes from the center of the cylinder to the
        #        center of the shell.
        return self.particle_radius, 0

    def get_left_scalingcenter(self):
        # same here
        return self.particle_radius, 0

    def get_right_scalingangle(self):
        return 0

    def get_left_scalingangle(self):
        return 0

#####
class CylindricalSurfacePairtestShell(CylindricaltestShell, Others):

    def __init__(self):
        # scaling parameters
        self.dzdr_right = numpy.inf
        self.drdz_right = 0.0
        self.r0_right   = max(particle_radius1, particle_radius2)
        self.z0_right   = 0.0
        self.dzdr_left  = numpy.inf
        self.drdz_left  = 0.0
        self.r0_left    = max(particle_radius1, particle_radius2)
        self.z0_left    = 0.0

#####
class PlanarSurfaceInteractiontestShell(CylindricaltestShell, Others):

    def __init__(self):
        # scaling parameters
        self.dzdr_right = 1.0
        self.drdz_right = 1.0
        self.r0_right   = 0.0
        self.z0_right   = distance_particle_refpoint
        self.dzdr_left  = 0.0
        self.drdz_left  = numpy.inf
        self.r0_left    = 0.0
        self.z0_left    = particle_radius

    def get_orientation_vector(self):
        result = do_calculation
        return result

    def get_searchpoint(self):
        result = calculate_searchpoint
        return result

    def get_referencepoint(self):
        return projected_point_of_particle

    def get_min_dr_dzright_dzleft(self):
        dz_right, r = calc_based_on_scaling_stuff
        dz_left = particle_radius
        return (dr, dz_right, dz_left)

    def get_max_dr_dzright_dzleft(self):
        result = calc_based_on_scaling_stuff
        return (dr, dz_right, dz_left)

    def get_right_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note that we assume cylindrical symmetry
        # Note also that it is relative to the 'side' (right/left) of the cylinder
        # note calculate this only once since 'orientation_z' doens't change
        # for different shells -> scalingcenter is a fixed point
        h0_right = distance_particle_surface
        return 0, h0_right

    def get_left_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note that we assume cylindrical symmetry
        # Note also that it is relative to the 'side' (right/left) of the cylinder
        # note calculate this only once since orientation_z doesn't change
        # for difference shells -> scalingcenter is a fixed point
        return 0, particle_radius

    def get_right_scalingangle(self):
        return Pi/4.0

    def get_left_scalingangle(self):
        return Pi/2.0

#####
class CylindricalSurfaceInteractiontestShell(CylindricaltestShell, Others):

    def __init__(self):

        # scaling parameters
        self.dzdr_right = 1.0
        self.drdz_right = 1.0
        self.r0_right   = 0.0
        self.z0_right   = calculate_it
        self.dzdr_left  = 1.0
        self.drdz_left  = 1.0
        self.r0_left    = 0.0
        self.z0_left    = calculate_it (same as above)

    def get_orientation_vector(self):
        return structure.shape.unit_z

    def get_searchpoint(self):
        return projected_point_of_particle

    def get_referencepoint(self):
        return projected_point_of_particle

    def get_min_dr_dzright_dzleft(self):
        result = calc_based_on_scaling_stuff
        return (dr, dz_right, dz_left)
        
    def get_max_dr_dzright_dzleft(self):
        result = calc_based_on_scaling_stuff
        return (dr, dz_right, dz_left)

    def get_right_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note that we assume cylindrical symmetry
        # Note also that it is relative to the 'side' (right/left) of the cylinder
        # note calculate this only once since 'orientation_z' doens't change
        # for different shells -> scalingcenter is a fixed point
        h0_right = smt
        return 0, h0_right

    def get_left_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note that we assume cylindrical symmetry
        # Note also that it is relative to the 'side' (right/left) of the cylinder
        # note calculate this only once since orientation_z doesn't change
        # for difference shells -> scalingcenter is a fixed point
        h0_left = h0_right
        return 0, h0_left

    def get_right_scalingangle(self):
        return bla

    def get_left_scalingangle(self):
        return Pi/2.0

#####
class MixedPair3D2DtestShell(CylindricaltestShell, Others):

    def __init__(self, single2D, single3D):

        # scaling parameters
        self.dzdr_right = calculate_it
        self.drdz_right = calculate_it
        self.r0_right   = 0.0
        self.z0_right   = calculate_it
        self.dzdr_left  = 0.0
        self.drdz_left  = numpy.inf
        self.r0_left    = 0.0
        self.z0_left    = particle2D_radius

    def get_orientation_vector(self):
        result = do_calculation
        return result

    def get_searchpoint(self):
        return caculated_search_point

    def get_referencepoint(self):
        return CoM

    def get_min_dr_dzright_dzleft(self):
        dz_left = particle_radius
        dr, dz_right = calc_based_on_scaling_stuff
        return (dr, dz_right, dz_left)
        
    def get_max_dr_dzright_dzleft(self):
        dz_left = particle_radius
        dr, dz_right = calc_based_on_scaling_stuff
        return (dr, dz_right, dz_left)

    def get_right_scalingcenter(self):
        # returns the scaling center in the cylindrical coordinates r, z of the shell
        # Note that we assume cylindrical symmetry
        # Note also that it is relative to the 'side' (right/left) of the cylinder
        return 0.0, self.z_right(0.0)

    def get_left_scalingcenter(self):
        return 0.0, self.z_left(0.0)

    def get_right_scalingangle(self):
        drdz =  z_scaling_factor * ( sqrt_DRDr + max( D1/D_r, D2/D_r ))
        angle = math.atan( drdz )
        return angle

    def get_left_scalingangle(self):
        return Pi/2.0

    def z_right(self, r):
        # calculate a_r such that the expected first-passage for the CoM and IV are equal
        a_r1 = (r - radius1 + r0*sqrt_DRDr ) / (sqrt_DRDr + (D1/D_r) )
        a_r2 = (r - radius2 + r0*sqrt_DRDr ) / (sqrt_DRDr + (D2/D_r) )
        # take the smallest that, if entered in the function for r below, would lead to this z_right
        a_r = min (a_r1, a_r2)

        return (a_r/z_scaling_factor) + radius2

    def r_right(self, z):
        # we first calculate the a_r, since it is the only radius that depends on z_right only.
        a_r = (z_right - radius2) * self.z_scaling_factor

        # We equalize the estimated first passage time for the CoM (2D) and IV (3D) for a given a_r
        # Note that for the IV we only take the distance to the outer boundary into account.
        a_R = (a_r - r0)*sqrt_DRDr

        # We calculate the maximum space needed for particles A and B based on maximum IV displacement
        iv_max = max( (D1/D_r * a_r + radius1),
                      (D2/D_r * a_r + radius2))

        return a_R + iv_max

    def z_left(self, r):
        return single1.pid_particle_pair[1].radius

    def r_left(self, z):
        return numpy.inf


    def get_z_scaling_factor(self):
        D2d = self.single2D.pid_partcle_pair[1].D
        D3d = self.single3D.pid_partcle_pair[1].D
        return math.sqrt( (D2d + D3d) / D3d)

#####
#class MixedPair3D1DtestShell(CylindricaltestShell, Others):
