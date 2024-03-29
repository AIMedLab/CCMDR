import numpy as np 
import pandas as pd
import random
from random import sample
import scipy 
from scipy.sparse import csr_matrix
from sklearn import linear_model
from sklearn.linear_model import LassoCV
from regressors import stats


def Intersection(nums1, nums2):
	return list(set(nums1) & set(nums2))


def compare(DU, T1, T2='NO'):
	DD = []
	if type(DU) == pd.Series:
		Time = DU['Use Time']
		if T2 == 'NO':
			if T1 >= Time:
				DD.append(DU['GeneName'])
		else:
			if T1 < Time and T2 >= Time:
				DD.append(DU['GeneName'])

	else:
		if T2 == 'NO':
			DU = DU[(DU['Use Time'] <= T1)]
			DD = DU['GeneName']
			if type(DD) == str:
				DD = DD.split('|')
			else:
				DD = DD.tolist()
		else:
			DU = DU[(DU['Use Time'] > T1) & (DU['Use Time'] <= T2)]
			DD = DU['GeneName']
			if type(DD) == str:
				DD = DD.split('|')
			else:
				DD = DD.tolist()

	return DD



random_seed = 123
random.seed(random_seed)

TestName = 'UREA_NITROGEN_test'
TestName = TestName[:-5]

LabTest = pd.read_csv('Patient_LabTest_Information.csv')
LabTest.set_index(['Patient ID'], inplace=True)
LabTest = LabTest[LabTest['Lab Name']==TestName]
Drug = pd.read_csv('GENNME_STAT_mapped.csv')
DrugUse = pd.read_csv('Patient_Prescription_Information.csv')
DrugUse.set_index(["Patient ID"], inplace=True)


##### Encode the gene name of drug
DrugList = list(Drug['GeneName'])
DrugNum = len(DrugList)

####### Turnn Drug to ID
DrugDict = {}
next_id = 0
for x in DrugList:
	DrugDict[x] = next_id
	next_id += 1


############## Drug embedding 
def Embedding(BatchList, DN = DrugNum):
	BatchNum = len(BatchList)
	X =  np.zeros((BatchNum, DN))

	for i in range(BatchNum):
		if not BatchList[i]:
			continue
		for d in BatchList[i]:
			X[i, DrugDict[d]] = 1.0

	return X 


##### Extract the patient ID 
PID1 = LabTest.index.tolist()
PID2 = DrugUse.index.tolist()
# PID1 = pd.value_counts(PID1).to_frame()
# PID1 = PID1.index.tolist()

PID = Intersection(PID1, PID2)
PID.sort()

LabTest  = LabTest.loc[PID]
DrugUse = DrugUse.loc[PID]


TestTime = {}

for pi in PID:
	TestTime[pi] = []
	TS = LabTest.loc[pi]['Test Time']
	if type(TS) == str:
		TestTime[pi].append(TS)
	else:
		TestTime[pi] = TestTime[pi] + TS.tolist()

X = []
for item in TestTime.items():
	DT = DrugUse.loc[item[0]]
	
	for i in range(len(item[1])):
		if i == 0:
			t1 = item[1][i]
			dd = compare(DT, t1)	
		else:
			t1 = item[1][i-1]
			t2 = item[1][i]
			dd = compare(DT, t1, t2)
		dd = list(set(dd))
		X.append(dd)
	
X = Embedding(X)
DF_X = pd.DataFrame(X, index=LabTest.index, columns=DrugList)
DF_X.to_csv('X/Encodding_X_'+TestName+'.csv')
LabTest.to_csv('LabTest/'+TestName+'_test.csv')


DrugUse = pd.read_csv('X/Encodding_X_'+TestName+'.csv')
DrugUse.set_index(['Patient ID'], inplace=True)

PL = DrugUse.index
PL = list(set(PL))
PL.sort()

LabTest = pd.read_csv('LabTest/'+TestName+'_test.csv')
LabTest.set_index(['Patient ID'], inplace=True)
LabTest = LabTest.loc[PL]

emp = np.sum(DrugUse.values, 1)==0
DrugUse = DrugUse.loc[~emp]
LabTest = LabTest.loc[~emp]
print(LabTest.shape)

PL = DrugUse.index
PL = list(set(PL))
PL.sort()

Xava = DrugUse.groupby(DrugUse.index)[DrugUse.columns].mean()
Yava = LabTest.groupby(LabTest.index)['Lab Test Value'].mean()



def buildZ(n, dimension):
	Z_values = []
	Z_row_indices = []
	Z_col_indices = []
	row = 0
	col = 0

	for x in n:
		# n = DrugUse.loc[ind].shape[0]
		# Z[row:row+n, i] = 1.0
		# n += 1
		# row += n
		for i in range(int(x)):
			Z_row_indices.append(row+i)
			Z_col_indices.append(col)
			Z_values.append(1.0)
		row = row + x
		col = col + 1

	Z = csr_matrix((Z_values, (Z_row_indices, Z_col_indices)), shape=dimension)

	return Z


def buildD(s, dimension):
	
	D_values = []
	D_row_indices = []
	D_col_indices = []
	row = 0
	col = 0

	for x in s:
		for i in range(int(x)):
			D_row_indices.append(row+i)
			D_col_indices.append(col+i)
			D_values.append(-1.0)
			D_row_indices.append(row+i)
			D_col_indices.append(col+i+1)
			D_values.append(1.0)
		row = row + x
		col = col + x+1

	D_values = np.array(D_values)
	D_row_indices = np.array(D_row_indices).reshape(-1)
	D_col_indices = np.array(D_col_indices).reshape(-1)


	D = csr_matrix((D_values, (D_row_indices, D_col_indices)),  shape=dimension)

	return D



def LeastR(bt, PID, count):

	X = DrugUse.loc[PID][DrugUse.columns]

	nn = pd.value_counts(X.index).to_frame()
	nn = nn.sort_index()
	nn = nn.values
	S = np.array(nn)-1

	X = X.values
	Y = np.array(LabTest.loc[PID]['Lab Test Value'])
	Y = Y.reshape(-1,1)

	Xbar = Xava.loc[PID]
	Ybar = Yava.loc[PID]

	Xbar = Xbar.values
	Ybar = Ybar.values
	Ybar = Ybar.reshape(-1,1)

	t = np.random.randn(Y.shape[0], 1)

	Z = buildZ(nn, (Y.shape[0], len(PID)))
	# D = buildD(S, (np.sum(S), Y.shape[0]))

	delta = X - Z.dot(Xbar)
	Phi = Y - Z.dot(Ybar) - t

	# delta = D.dot(X)
	# Phi = D.dot(Y)


	Phi = Phi.reshape(-1)

	reg = linear_model.LassoCV(alphas=[0.0039], cv=5)
	reg.fit(delta, Phi)
	bt_new = reg.coef_.reshape(-1,1)


	p_value = stats.coef_pval(reg, delta, Phi)[1:]
	p_value = p_value.reshape(-1,1)
	bt_new = (bt*count)/(count+1) + bt_new/(count+1)

	return bt_new, p_value



Beta = np.random.rand(392, 1)
converged = False
c = 0

PID = PL
PID.sort()

Beta_new, P = LeastR(Beta, PID, c)
data = np.hstack((Beta_new, P))


Effect = pd.DataFrame(data, index=DrugUse.columns, columns=['Effect Value', 'P Value'])
Effect.index.name = 'Generic Name'
Effect = Effect.sort_values(by='Effect Value', ascending= True)

Effect.to_csv('CompResult/Drug2'+TestName+'.csv')





