import sys
import numpy

import vtk

import random

from datafile import load_header


zoom = 1e6

class Particles:
    def __init__(self):
        self.pos = numpy.array([[]])
        self.pos.shape = (0, 3)
        self.radii = numpy.array([])


colors = [(1, .2, .2),  (.2,.2,1), (.8, .8, .3)]


def addParticles(ren, positions, radii, n):

    for pos in positions:
        
        addParticle(ren, pos, radii[n], colors[n])



def addParticle(ren, pos, radius, color):
    vpos = pos * zoom
    sphere = vtk.vtkSphereSource()
    sphere.SetCenter(vpos) #vpos[0],vpos[1],vpos[2] ) )
    sphere.SetRadius(radius * zoom)
    sphereMapper = vtk.vtkPolyDataMapper()
    sphereMapper.SetInputConnection(sphere.GetOutputPort())
    
    sphereActor = vtk.vtkActor()
    sphereActor.SetMapper(sphereMapper)
    sphereActor.GetProperty().SetColor(color)
    
    ren.AddActor(sphereActor)


def writeFrame(particles, renWin, header):

    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)

    size = header['worldSize'] * zoom

    cube = vtk.vtkCubeSource()
    cube.SetBounds(0,size,0,size,0,size)
    cubeMapper = vtk.vtkPolyDataMapper()
    cubeMapper.SetInputConnection(cube.GetOutputPort())
    cubeActor = vtk.vtkActor()
    cubeActor.SetMapper(cubeMapper)

    cubeActor.GetProperty().SetRepresentationToWireframe()
#    cubeActor.GetProperty().EdgeVisibilityOn()
#     cubeActor.GetProperty().SetEdgeColor(1.,1.,0.)
    cubeActor.GetProperty().SetOpacity(0.1)    
    ren.AddActor(cubeActor)
    

    renWin.AddRenderer(ren)
    renWin.SetSize(400, 400)

    #iren = vtk.vtkRenderWindowInteractor()
    #iren.SetRenderWindow(renWin)
    #style = vtk.vtkInteractorStyleTrackballCamera()
    #iren.SetInteractorStyle(style)
    #iren.Initialize()

    for n, id in enumerate(particlePools.keys()):
        particles = particlePools[id]
        addParticles(ren, particles.pos, particles.radii, n)
        print n

    text = vtk.vtkTextActor()
    text.SetInput('t = %10.9f' % float(header['t']))
    text.GetTextProperty().SetColor(0,0,0)
    text.SetDisplayPosition(300, 385)
    ren.AddActor2D(text)


    ren.ResetCamera(0,size,0,size,0,size)
    camera = ren.GetActiveCamera()
    camera.Zoom(1.4)
    pos = camera.GetPosition()
    camera.SetPosition(pos[0]*1.6, pos[1]*1.4, pos[2])
    #camera.Dolly(1.5)
    #camera.SetDistance(.1)


    renWin.Render()

    w2if = vtk.vtkWindowToImageFilter()
    w2if.SetInput(renWin)

    outfilename = header['name'] + '_' + str(header['count']).zfill(4) + '.png'
        
    wr = vtk.vtkPNGWriter()
    wr.SetInputConnection(w2if.GetOutputPort())
    wr.SetFileName(outfilename)
    wr.Write()

    renWin.RemoveRenderer(ren)




def loadParticles(filename):

    file = open(filename)

    particlePools = {}

    for line in file.readlines():
        #print line
        if line[0] == '#':
            continue

        id, x, y, z, r = line.split()

        if not id in particlePools:
            particlePools[id] = Particles()

        pool = particlePools[id]
        
        pool.pos = numpy.append(pool.pos, 
                                [[float(x), float(y), float(z)]],
                                axis=0)

        pool.radii = numpy.append(pool.radii, float(r))


    file.close()

    return particlePools
                        


if __name__ == '__main__':

    import glob

    inpattern = sys.argv[1]

    infiles = glob.glob(inpattern)
    print infiles

    renWin = vtk.vtkRenderWindow()
    renWin.MappedOff()
    renWin.OffScreenRenderingOn()

    for infile in infiles:

        header = load_header(infile)
        print header

        particlePools = loadParticles(infile)

        writeFrame(particlePools, renWin, header)


