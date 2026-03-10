import Part
dir = '/home/node/clawd/apps/dxf2step/jobs/test_png2_20260228_063431'
for f in ['ProjItem.step', 'ProjItem001.step', 'View.step']:
    s = Part.read(dir + '/' + f)
    bb = s.BoundBox
    print(f + ': X=' + str(round(bb.XMin,1)) + '..' + str(round(bb.XMax,1))
          + '  Y=' + str(round(bb.YMin,1)) + '..' + str(round(bb.YMax,1))
          + '  Z=' + str(round(bb.ZMin,1)) + '..' + str(round(bb.ZMax,1))
          + '  Vol=' + str(round(s.Volume,1))
          + '  Faces=' + str(len(s.Faces)))
